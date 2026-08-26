"""Storage allocation evaluator enforcing monotonic capacity growth."""
from rds.errors import StorageShrinkError


class StorageEvaluator:
    """Evaluates allocated storage modifications."""

    @staticmethod
    def validate_storage_allocation(current_allocated_gb: int, requested_allocated_gb: int) -> None:
        """Enforce that storage can only increase monotonically."""
        if requested_allocated_gb <= current_allocated_gb:
            raise StorageShrinkError(
                f"Requested storage ({requested_allocated_gb} GB) must be strictly greater "
                f"than current allocated storage ({current_allocated_gb} GB)"
            )
