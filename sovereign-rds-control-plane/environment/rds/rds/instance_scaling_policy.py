"""Storage auto-scaling policy, IOPS threshold evaluator, and scale-up window manager."""
from typing import Any, Dict, Optional, Tuple

class InstanceScalingPolicy:
    """Evaluates storage auto-scaling triggers and instance class scale-up windows."""

    def __init__(self, max_allocated_storage_gb: int = 10000, scaling_threshold_pct: float = 10.0):
        self.max_allocated_storage_gb = max_allocated_storage_gb
        self.scaling_threshold_pct = scaling_threshold_pct

    def evaluate_storage_autoscale(
        self,
        current_storage_gb: int,
        free_storage_space_bytes: int
    ) -> Tuple[bool, int, str]:
        """Evaluate if free storage space is below threshold and calculate next storage size."""
        current_bytes = current_storage_gb * 1024 * 1024 * 1024
        if current_bytes <= 0:
            return False, current_storage_gb, "Invalid storage size"

        free_pct = (free_storage_space_bytes / float(current_bytes)) * 100.0

        if free_pct <= self.scaling_threshold_pct:
            # Auto-scale up by 10% or 50 GB, whichever is larger
            increment_gb = max(50, int(current_storage_gb * 0.10))
            new_storage_gb = min(self.max_allocated_storage_gb, current_storage_gb + increment_gb)

            if new_storage_gb > current_storage_gb:
                return True, new_storage_gb, f"Free space ({free_pct:.1f}%) below threshold ({self.scaling_threshold_pct}%); scaling to {new_storage_gb} GB"

        return False, current_storage_gb, "Storage capacity sufficient"
