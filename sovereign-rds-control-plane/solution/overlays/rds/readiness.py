"""Control plane readiness health check evaluator."""
from typing import Any, Dict, List


class ReadinessEvaluator:
    """Evaluates control plane system readiness."""

    @staticmethod
    def evaluate_readiness(
        instances: List[Dict[str, Any]],
        unprocessed_events_count: int,
        failing_probes_count: int
    ) -> Dict[str, Any]:
        """Evaluate control plane readiness status."""
        total = len(instances)
        available = sum(1 for i in instances if i.get("status") == "AVAILABLE")

        is_ready = (
            total > 0
            and available == total
            and unprocessed_events_count == 0
            and failing_probes_count == 0
        )

        return {
            "status": "READY" if is_ready else "UNHEALTHY",
            "total_instances": total,
            "available_instances": available,
            "unprocessed_events": unprocessed_events_count,
            "failing_health_probes": failing_probes_count,
        }
