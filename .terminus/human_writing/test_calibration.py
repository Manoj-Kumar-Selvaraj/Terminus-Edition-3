"""Regression tests for dataset-backed instruction-writing calibration."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from calibration import CalibrationError, HumanWritingCalibrationPlanner, sample_ids


ROOT = Path(__file__).resolve().parents[2]


class HumanWritingCalibrationTests(unittest.TestCase):
    """Validate deterministic selection, independence, and safety invariants."""

    def test_registry_is_valid_and_weights_are_normalized(self) -> None:
        planner = HumanWritingCalibrationPlanner(ROOT)
        result = planner.validate()
        self.assertEqual(result["status"], "VALID")
        self.assertEqual(result["enabled_dataset_count"], 4)
        self.assertGreaterEqual(result["seed_sample_count"], 30)

    def test_pair_is_deterministic(self) -> None:
        planner = HumanWritingCalibrationPlanner(ROOT)
        first = planner.build_pair(task_id="demo-task", domain="kubernetes recovery")
        second = planner.build_pair(task_id="demo-task", domain="kubernetes recovery")
        self.assertEqual(first, second)

    def test_writer_and_reviewer_study_sets_are_disjoint(self) -> None:
        planner = HumanWritingCalibrationPlanner(ROOT)
        pair = planner.build_pair(task_id="demo-task", domain="terraform automation")
        writer = sample_ids(pair["writer"]["local_seed_samples"])
        reviewer = sample_ids(pair["reviewer"]["local_seed_samples"])
        self.assertFalse(writer & reviewer)
        self.assertEqual(pair["independence"]["status"], "PASS")

    def test_reviewer_has_more_constraint_and_anti_template_contrasts(self) -> None:
        planner = HumanWritingCalibrationPlanner(ROOT)
        pair = planner.build_pair(task_id="demo-task", domain="distributed systems")
        writer_kinds = [item["kind"] for item in pair["writer"]["local_seed_samples"]]
        reviewer_kinds = [item["kind"] for item in pair["reviewer"]["local_seed_samples"]]
        self.assertEqual(writer_kinds.count("constraint_pair"), 2)
        self.assertEqual(reviewer_kinds.count("constraint_pair"), 3)
        self.assertEqual(writer_kinds.count("anti_template"), 1)
        self.assertEqual(reviewer_kinds.count("anti_template"), 2)

    def test_disabled_dataset_cannot_have_weight(self) -> None:
        registry = json.loads(
            (ROOT / ".terminus/human_writing/dataset_registry.json").read_text(
                encoding="utf-8"
            )
        )
        catalog = (ROOT / ".terminus/human_writing/seed_catalog.json").read_text(
            encoding="utf-8"
        )
        for dataset in registry["datasets"]:
            if dataset["id"] == "github-human-codereview":
                dataset["reviewer_weight"] = 0.1
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / ".terminus/human_writing"
            target.mkdir(parents=True)
            (target / "dataset_registry.json").write_text(
                json.dumps(registry), encoding="utf-8"
            )
            (target / "seed_catalog.json").write_text(catalog, encoding="utf-8")
            with self.assertRaises(CalibrationError):
                HumanWritingCalibrationPlanner(root)

    def test_domain_matching_prefers_relevant_human_examples(self) -> None:
        planner = HumanWritingCalibrationPlanner(ROOT)
        pair = planner.build_pair(task_id="dns-task", domain="coredns kubernetes dns")
        writer_ids = pair["writer"]["local_seed_sample_ids"]
        self.assertTrue({"HC-027", "HC-028"} & set(writer_ids))

    def test_training_directives_preserve_requirements(self) -> None:
        planner = HumanWritingCalibrationPlanner(ROOT)
        pair = planner.build_pair(task_id="safe-task", domain="security operations")
        writer_text = " ".join(pair["writer"]["directives"]).lower()
        reviewer_text = " ".join(pair["reviewer"]["directives"]).lower()
        self.assertIn("never omit a material requirement", writer_text)
        self.assertIn("completeness before style", reviewer_text)
        self.assertIn("never as the desired engineering voice", reviewer_text)


if __name__ == "__main__":
    unittest.main()
