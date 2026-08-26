"""Control plane evidence collection and report snapshot publisher."""
import json
from pathlib import Path
from typing import Any, Dict
from rds.digest import compute_stable_digest


class EvidencePublisher:
    """Publishes canonical control plane state snapshot reports with deterministic SHA-256 digests."""

    @staticmethod
    def publish_report(report_data: Dict[str, Any], output_dir: Path) -> str:
        """Format canonical report JSON with sorted keys and compute report digest."""
        output_dir.mkdir(parents=True, exist_ok=True)

        instances = [
            {
                "instance_id": i.get("instance_id"),
                "status": i.get("status"),
                "db_instance_class": i.get("db_instance_class"),
                "allocated_storage_gb": i.get("allocated_storage_gb"),
                "pending_reboot_parameters": i.get("pending_reboot_parameters", False),
                "multi_az": i.get("multi_az", False),
            }
            for i in report_data.get("instances", [])
        ]

        stable_subset = {
            "status": report_data.get("status"),
            "total_instances": report_data.get("total_instances", 0),
            "available_instances": report_data.get("available_instances", 0),
            "active_replicas": report_data.get("active_replicas", 0),
            "pending_events": report_data.get("pending_events", 0),
            "instances": sorted(instances, key=lambda x: str(x.get("instance_id"))),
        }

        digest = compute_stable_digest(stable_subset)
        report_data["report_digest"] = digest

        report_file = output_dir / "rds-snapshot.json"
        report_file.write_text(
            json.dumps(report_data, indent=2, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
        )

        # Companion operator artifacts (no per-file digest).
        with (output_dir / "instances.jsonl").open("w", encoding="utf-8") as fh:
            for inst in stable_subset["instances"]:
                fh.write(json.dumps(inst, sort_keys=True, default=str) + "\n")
        events = report_data.get("events") or report_data.get("outbox_events") or []
        with (output_dir / "events.jsonl").open("w", encoding="utf-8") as fh:
            for evt in events:
                fh.write(json.dumps(evt, sort_keys=True, default=str) + "\n")
        health = {
            "status": report_data.get("status"),
            "total_instances": stable_subset["total_instances"],
            "available_instances": stable_subset["available_instances"],
            "active_replicas": stable_subset["active_replicas"],
            "pending_events": stable_subset["pending_events"],
        }
        (output_dir / "health.json").write_text(
            json.dumps(health, indent=2, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
        )
        return digest
