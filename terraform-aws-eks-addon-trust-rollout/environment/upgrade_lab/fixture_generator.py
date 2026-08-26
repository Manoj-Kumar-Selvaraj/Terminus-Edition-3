"""Deterministic estate fixture generator producing 12,500+ primary records."""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List


class FixtureGenerator:
    """Generator for deterministic upgrade lab dataset fixtures."""

    def __init__(self, seed: int = 42):
        self.seed = seed
        random.seed(seed)
        self.record_count = 0

    def generate_telemetry_history(self, count: int = 12000) -> List[Dict[str, Any]]:
        """Generate 12,000 deterministic cluster telemetry and metric records."""
        base_time = datetime(2026, 8, 20, 12, 0, 0, tzinfo=timezone.utc)
        records: List[Dict[str, Any]] = []

        components = ["coredns", "kube-proxy", "vpc-cni", "ebs-csi", "aws-load-balancer-controller", "karpenter"]
        nodepools = ["system", "apps", "batch"]

        for i in range(count):
            ts = base_time + timedelta(seconds=i * 5)
            comp = components[i % len(components)]
            np = nodepools[i % len(nodepools)]

            records.append({
                "metric_id": f"metric-{i:06d}",
                "timestamp": ts.isoformat(),
                "component": comp,
                "nodepool": np,
                "cpu_utilization": round(random.uniform(10.0, 85.0), 2),
                "memory_mb": random.randint(128, 4096),
                "pod_count": random.randint(1, 25),
                "healthy": True,
            })
            self.record_count += 1

        return records

    def generate_interruption_events(self, count: int = 500) -> List[Dict[str, Any]]:
        """Generate 500 deterministic spot and on-demand node interruption event records."""
        base_time = datetime(2026, 8, 21, 0, 0, 0, tzinfo=timezone.utc)
        events: List[Dict[str, Any]] = []

        event_types = ["SPOT_INTERRUPTION_NOTICE", "NODE_REBALANCE_RECOMMENDATION", "CAPACITY_UNAVAILABLE"]
        nodepools = ["batch", "apps", "system"]

        for i in range(count):
            ts = base_time + timedelta(minutes=i * 10)
            etype = event_types[i % len(event_types)]
            np = nodepools[i % len(nodepools)]

            events.append({
                "event_id": f"event-{i:04d}",
                "timestamp": ts.isoformat(),
                "event_type": etype,
                "nodepool": np,
                "node_name": f"ip-10-0-{i % 10}-{i % 250}.ec2.internal",
                "handled": True,
                "workload_migrated": True,
            })
            self.record_count += 1

        return events


def generate_estate_fixtures(data_dir_path: Any = None) -> int:
    """Generate deterministic estate fixtures to reach 12,500+ primary records."""
    import json
    from pathlib import Path

    data_dir = Path(data_dir_path) if data_dir_path is not None else Path("/app/data")
    data_dir.mkdir(parents=True, exist_ok=True)
    gen = FixtureGenerator(seed=42)
    telemetry = gen.generate_telemetry_history(12000)
    interruptions = gen.generate_interruption_events(500)
    (data_dir / "telemetry_history.json").write_text(
        json.dumps(telemetry, indent=2) + "\n", encoding="utf-8"
    )
    (data_dir / "interruption_events.json").write_text(
        json.dumps(interruptions, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Generated {gen.record_count} primary estate records")
    return gen.record_count
