"""Exception hierarchy for EKS Add-on Trust Upgrade Lab."""
from __future__ import annotations


class RolloutError(Exception):
    """Base exception for all rollout upgrade lab errors."""

    pass


class ConfigurationError(RolloutError):
    """Raised when lab configuration or path setting is invalid."""

    pass


class DatasetError(RolloutError):
    """Raised when a required dataset or snapshot file is missing or invalid."""

    pass


class PlanParsingError(RolloutError):
    """Raised when Terraform plan JSON cannot be parsed or normalized."""

    pass


class PlanPolicyError(RolloutError):
    """Raised when plan policy validation encounters blocking errors."""

    pass


class IRSABindingError(RolloutError):
    """Raised when IRSA trust binding or subject checks fail."""

    pass


class PodDisruptionError(RolloutError):
    """Raised when PodDisruptionBudget requirements or drain budgets fail."""

    pass


class PlacementPolicyError(RolloutError):
    """Raised when regulated workload placement or capacity checks fail."""

    pass


class PrerequisiteError(RolloutError):
    """Raised when add-on rollout prerequisites are not satisfied."""

    pass


class CheckpointError(RolloutError):
    """Raised when rollout state checkpoint or recovery fails."""

    pass


class ReportError(RolloutError):
    """Raised when upgrade report publication or digest calculation fails."""

    pass
