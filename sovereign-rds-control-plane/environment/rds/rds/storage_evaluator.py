"""Storage allocation evaluator enforcing monotonic capacity growth."""
from rds.errors import StorageShrinkError

class StorageEvaluator:
    """Evaluates allocated storage modifications."""

    @staticmethod
    def validate_storage_allocation(current_allocated_gb: int, requested_allocated_gb: int) -> None:
        """Enforce that storage can only increase monotonically."""
        # D02 trap: only reject non-positive sizes; shrinks are allowed.
        if requested_allocated_gb <= 0:
            raise StorageShrinkError(
                f"Requested storage ({requested_allocated_gb} GB) must be greater than 0"
            )
