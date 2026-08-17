"""Regression tests for the human-writing retrieval/evaluation/learning loop."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from calibration import HumanWritingCalibrationPlanner
from contamination import analyze_contamination
from corpus_cache import CorpusCacheError, HumanWritingCorpusCache
from evaluation import EvaluationError, aggregate_ab_results, prepare_blind_ab, score_blind_ab
from learning_loop import HumanWritingLearningStore
from materialize import CorpusMaterializer
from preference_store import TerminusPreferenceStore


ROOT = Path(__file__).resolve().parents[2]


class HumanWritingLearningLoopTests(unittest.TestCase):
    def test_cache_enforces_dataset_role_and_attribution_policy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache = HumanWritingCorpusCache(ROOT, Path(tmp) / "cache.sqlite3")
            with self.assertRaises(CorpusCacheError):
                cache.upsert(
                    {
                        "dataset_id": "github-human-codereview",
                        "source_id": "x",
                        "source_revision": "rev1",
                        "domain": "python",
                        "artifact_type": "review",
                        "role_signal": "reviewer",
                        "structural_summary": "specific review",
                    }
                )
            with self.assertRaises(CorpusCacheError):
                cache.upsert(
                    {
                        "dataset_id": "code-review-bench-human-annotations",
                        "source_id": "x",
                        "source_revision": "rev1",
                        "annotation_kind": "expert",
                        "domain": "python",
                        "artifact_type": "review",
                        "role_signal": "writer",
                        "structural_summary": "reviewer-only evidence",
                    }
                )
            with self.assertRaises(CorpusCacheError):
                cache.upsert(
                    {
                        "dataset_id": "h4-stack-exchange-preferences",
                        "source_id": "q1",
                        "source_url": "https://example.invalid/q1",
                        "source_revision": "rev1",
                        "source_site": "stackoverflow",
                        "domain": "kubernetes recovery",
                        "artifact_type": "incident",
                        "role_signal": "writer",
                        "structural_summary": "restart symptom and expected state",
                        "text": "A retained source text requiring attribution.",
                    }
                )

    def test_cache_search_prefers_domain_match_hides_text_and_applies_floor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache = HumanWritingCorpusCache(ROOT, Path(tmp) / "cache.sqlite3")
            cache.upsert(
                {
                    "dataset_id": "h4-stack-exchange-preferences",
                    "source_id": "q1",
                    "source_url": "https://example.invalid/q1",
                    "source_revision": "rev1",
                    "source_site": "stackoverflow",
                    "author": "A",
                    "author_url": "https://example.invalid/a",
                    "domain": "kubernetes recovery",
                    "artifact_type": "incident",
                    "role_signal": "writer",
                    "structural_summary": "restart failure after partial recovery",
                    "text": "The service restarts after partial recovery but repeats the same work.",
                }
            )
            results = cache.search(
                "kubernetes restart recovery",
                role_signal="writer",
                artifact_types=["incident"],
            )
            self.assertEqual(results[0]["source_id"], "q1")
            self.assertNotIn("retained_text", results[0])
            self.assertEqual(cache.search("fortran graphics shader", role_signal="writer"), [])

    def test_contamination_detects_partial_copy_inside_long_source(self) -> None:
        copied = (
            "the controller retries completed operations after restart and publishes "
            "a second result even though the first result was already committed"
        )
        source = "unrelated context " * 80 + copied + " unrelated tail" * 80
        draft = "Please investigate this behavior: " + copied + ". Preserve the existing API."
        result = analyze_contamination(
            draft,
            [{"source_key": "h4:q1", "text": source}],
        )
        self.assertEqual(result["status"], "REWRITE_REQUIRED")
        self.assertEqual(result["findings"][0]["source_key"], "h4:q1")
        self.assertNotIn(copied, json.dumps(result))

    def test_blind_ab_completeness_is_hard_gate_and_evaluator_is_independent(self) -> None:
        prepared = prepare_blind_ab(
            task_id="demo",
            baseline_text="Complete but formal instruction.",
            calibrated_text="Natural instruction.",
            requirement_contract_sha256="a" * 64,
            writer_actor_id="writer-1",
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
                "ai_template_signal": 1,
                "synthetic_completeness": 1,
                "rubric_mirroring": 1,
                "implementation_leakage": 0,
            }
        with self.assertRaises(EvaluationError):
            score_blind_ab(
                public_packet=prepared["public_packet"],
                sealed_mapping=prepared["sealed_mapping"],
                scores=scores,
                evaluator_actor_id="writer-1",
                evaluator_role="Instruction Reviewer",
            )
        result = score_blind_ab(
            public_packet=prepared["public_packet"],
            sealed_mapping=prepared["sealed_mapping"],
            scores=scores,
            evaluator_actor_id="reviewer-1",
            evaluator_role="Instruction Reviewer",
        )
        self.assertEqual(result["preferred_origin"], "baseline")
        self.assertTrue(result["evaluator_binding"]["independent_from_writer"])

    def test_blind_ab_material_implementation_leakage_disqualifies_variant(self) -> None:
        prepared = prepare_blind_ab(
            task_id="demo-leak",
            baseline_text="Complete normal instruction.",
            calibrated_text="Complete instruction with implementation diagnosis.",
            requirement_contract_sha256="b" * 64,
            writer_actor_id="writer-1",
        )
        scores = {}
        for label, origin in prepared["sealed_mapping"]["mapping"].items():
            scores[label] = {
                "requirement_completeness": 5,
                "technical_precision": 5,
                "human_information_selection": 5,
                "natural_grouping": 5,
                "implementation_distance": 5,
                "verbosity_fit": 5,
                "ai_template_signal": 0,
                "synthetic_completeness": 0,
                "rubric_mirroring": 0,
                "implementation_leakage": 3 if origin == "calibrated" else 0,
            }
        result = score_blind_ab(
            public_packet=prepared["public_packet"],
            sealed_mapping=prepared["sealed_mapping"],
            scores=scores,
            evaluator_actor_id="reviewer-1",
            evaluator_role="Blind A/B Evaluator",
        )
        self.assertEqual(result["preferred_origin"], "baseline")

    def test_ab_aggregate_ignores_unbound_results(self) -> None:
        summary = aggregate_ab_results(
            [
                {"preferred_origin": "calibrated", "evaluator_binding": {"independent_from_writer": True}},
                {"preferred_origin": "baseline", "evaluator_binding": {"independent_from_writer": True}},
                {"preferred_origin": "calibrated"},
            ]
        )
        self.assertEqual(summary["decided_results"], 2)
        self.assertAlmostEqual(summary["calibrated_win_rate"], 0.5)

    def test_learning_record_is_bound_and_tracks_reviewer_disagreement(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "outcomes.jsonl"
            store = HumanWritingLearningStore(ROOT, state)
            pair = HumanWritingCalibrationPlanner(ROOT).build_pair(
                task_id="t1", domain="security operations"
            )
            committed = "Accepted instruction content.\n"
            record = {
                "task_id": "t1",
                "task_commit": "1" * 40,
                "domain": "security operations",
                "calibration_pair_id": pair["pair_id"],
                "writer_calibration_id": pair["writer"]["calibration_id"],
                "reviewer_calibration_id": pair["reviewer"]["calibration_id"],
                "draft_sha256": "a" * 64,
                "accepted_sha256": hashlib.sha256(committed.encode()).hexdigest(),
                "requirement_count": 8,
                "requirement_completeness": "SUFFICIENT",
                "requirement_regression": False,
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
                "human_signal": "HIGH",
                "llmaj_writing_finding": False,
                "contamination_status": "PASS",
                "evidence_refs": {"instruction_reviewer_result_id": "review-1"},
            }
            with patch.object(store, "_git_file", return_value=committed):
                store.append(record)
            metrics = store.metrics()
            self.assertEqual(metrics["reviewer_disagreement_count"], 1)
            self.assertEqual(metrics["task_count"], 1)
            self.assertEqual(
                store.recommend_weights("writer")["status"], "INSUFFICIENT_DATA"
            )

    def test_native_preference_store_keeps_hashes_not_text_and_binds_chosen(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = TerminusPreferenceStore(ROOT, Path(tmp) / "prefs.jsonl")
            rejected = "This is a verbose synthetic draft."
            chosen = "Fix the restart path without duplicating committed work."
            with patch.object(store, "_git_file", return_value=chosen):
                record = store.append(
                    task_id="t1",
                    task_commit="1" * 40,
                    rejected_text=rejected,
                    chosen_text=chosen,
                    label_source="human_review",
                    reason_codes=["natural_grouping", "requirements_preserved"],
                    calibration_pair_id="hwpair-demo",
                    holdout_eligible=True,
                )
            rendered = json.dumps(record)
            self.assertNotIn(rejected, rendered)
            self.assertNotIn(chosen, rendered)
            self.assertTrue(record["chosen_task_artifact_bound"])

    def test_default_learning_paths_are_durable_knowledge_paths(self) -> None:
        learning = HumanWritingLearningStore(ROOT)
        preferences = TerminusPreferenceStore(ROOT)
        self.assertIn("/learning/knowledge/", learning.path.as_posix())
        self.assertIn("/learning/knowledge/", preferences.path.as_posix())

    def test_weight_recommendation_requires_controlled_attribution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "outcomes.jsonl"
            records = []
            for index in range(20):
                records.append(
                    {
                        "task_id": f"t{index}",
                        "dataset_ablation": {
                            "h4-stack-exchange-preferences": {
                                "controlled": True,
                                "role": "writer",
                                "quality_delta": 0.1,
                            }
                        },
                    }
                )
            state.write_text(
                "".join(json.dumps(record) + "\n" for record in records),
                encoding="utf-8",
            )
            store = HumanWritingLearningStore(ROOT, state)
            result = store.recommend_weights("writer")
            self.assertEqual(result["status"], "INSUFFICIENT_ATTRIBUTION")

    def test_materializer_binds_input_hash_revision_and_role(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "source.jsonl"
            input_path.write_text(
                json.dumps(
                    {
                        "source_id": "c1",
                        "source_url": "https://example.invalid/c1",
                        "domain": "security requirements",
                        "artifact_type": "preference_pair",
                        "structural_summary": "one relaxed constraint invalidates the response",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            materializer = CorpusMaterializer(ROOT, Path(tmp) / "cache.sqlite3")
            result = materializer.materialize(
                dataset_id="tulu3-constraint-preferences",
                input_path=input_path,
                source_revision="rev-123",
                role_signal="writer",
            )
            self.assertEqual(result["record_count"], 1)
            self.assertEqual(result["source_revision"], "rev-123")
            self.assertEqual(len(result["input_sha256"]), 64)

    def test_adapter_training_is_disabled_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = HumanWritingLearningStore(ROOT, Path(tmp) / "outcomes.jsonl")
            readiness = store.adapter_readiness()
            self.assertEqual(readiness["status"], "DISABLED")
            self.assertFalse(readiness["enabled"])


if __name__ == "__main__":
    unittest.main()
