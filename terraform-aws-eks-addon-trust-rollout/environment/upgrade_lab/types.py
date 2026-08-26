"""Data models and type definitions for the EKS Add-on Trust Upgrade Lab."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AddonPlanSpec:
    """Normalized add-on specification from Terraform plan."""

    addon_name: str
    addon_version: Optional[str]
    resolve_conflicts_on_update: Optional[str]
    service_account_role_arn: Optional[str]
    tags: Dict[str, str] = field(default_factory=dict)
    actions: List[str] = field(default_factory=list)
    address: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert specification to dictionary."""
        return {
            "addon_name": self.addon_name,
            "addon_version": self.addon_version,
            "resolve_conflicts_on_update": self.resolve_conflicts_on_update,
            "service_account_role_arn": self.service_account_role_arn,
            "tags": self.tags,
            "actions": self.actions,
            "address": self.address,
        }


@dataclass
class IRSARoleSpec:
    """Normalized IAM role specification for IRSA from Terraform plan."""

    name: Optional[str]
    subjects: List[str] = field(default_factory=list)
    tags: Dict[str, str] = field(default_factory=dict)
    actions: List[str] = field(default_factory=list)
    address: str = ""
    assume_role_policy: Any = None
    policy_actions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert specification to dictionary."""
        return {
            "name": self.name,
            "subjects": self.subjects,
            "tags": self.tags,
            "actions": self.actions,
            "address": self.address,
            "assume_role_policy": self.assume_role_policy,
            "policy_actions": self.policy_actions,
        }


@dataclass
class NodeGroupSpec:
    """Normalized node group specification from Terraform plan."""

    node_group_name: Optional[str]
    labels: Dict[str, str] = field(default_factory=dict)
    taints: List[Any] = field(default_factory=list)
    tags: Dict[str, str] = field(default_factory=dict)
    actions: List[str] = field(default_factory=list)
    address: str = ""
    subnet_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert specification to dictionary."""
        return {
            "node_group_name": self.node_group_name,
            "labels": self.labels,
            "taints": self.taints,
            "tags": self.tags,
            "actions": self.actions,
            "address": self.address,
            "subnet_ids": self.subnet_ids,
        }


@dataclass
class RegulatedPlacementSpec:
    """Normalized regulated placement specification from Terraform plan."""

    capacity_types: List[str] = field(default_factory=list)
    name: Optional[str] = None
    private_only: Optional[bool] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert specification to dictionary."""
        return {
            "capacity_types": self.capacity_types,
            "name": self.name,
            "private_only": self.private_only,
        }


@dataclass
class ProtectedResourceAction:
    """Resource tagged UpgradeProtected scheduled for delete/replace."""

    address: str
    actions: List[str]
    type: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert specification to dictionary."""
        return {
            "address": self.address,
            "actions": self.actions,
            "type": self.type,
        }


@dataclass
class NormalizedPlan:
    """Complete normalized representation of a Terraform show -json plan."""

    addons: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    roles: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    node_groups: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    regulated: Dict[str, Any] = field(default_factory=dict)
    protected_actions: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert normalized plan to dictionary."""
        return {
            "addons": self.addons,
            "roles": self.roles,
            "node_groups": self.node_groups,
            "regulated": self.regulated,
            "protected_actions": self.protected_actions,
        }


@dataclass
class PDBManifest:
    """Parsed Kubernetes PodDisruptionBudget manifest."""

    name: str
    namespace: str
    min_available: Any
    selector: Dict[str, str] = field(default_factory=dict)


@dataclass
class ServiceAccountManifest:
    """Parsed Kubernetes ServiceAccount manifest."""

    name: str
    namespace: str
    role_arn: str


@dataclass
class DeploymentManifest:
    """Parsed Kubernetes Deployment manifest."""

    name: str
    namespace: str
    replicas: int
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class RegulatedWorkloadManifest:
    """Parsed regulated workload placement manifest."""

    name: str
    namespace: Optional[str]
    nodepool: Optional[str]
    capacity_type: Optional[str]
    replicas: int
    kind: str


@dataclass
class ParsedK8sState:
    """Kubernetes cluster state collected from submitted manifests."""

    pdbs: List[Dict[str, Any]] = field(default_factory=list)
    service_accounts: List[Dict[str, Any]] = field(default_factory=list)
    deployments: List[Dict[str, Any]] = field(default_factory=list)
    nodepools: List[Dict[str, Any]] = field(default_factory=list)
    workloads: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class DrainResult:
    """Result of system node drain simulation."""

    node: str
    core_available: bool
    evicted_count: int
    blocked_count: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "node": self.node,
            "core_available": self.core_available,
            "evicted_count": self.evicted_count,
            "blocked_count": self.blocked_count,
        }


@dataclass
class InterruptionResult:
    """Result of node interruption simulation."""

    handled: bool
    regulated_still_on_demand: bool

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "handled": self.handled,
            "regulated_still_on_demand": self.regulated_still_on_demand,
        }


@dataclass
class UpgradeReport:
    """Final upgrade readiness report."""

    status: str
    reason: Optional[str]
    policy_errors: List[str]
    upgrade_order: List[str]
    steps: List[Dict[str, Any]]
    availability: Dict[str, bool]
    pdb_respected: bool
    drain_result: Dict[str, Any]
    irsa_bindings: Dict[str, Any]
    cross_service_denied: bool
    regulated_placement: Dict[str, Any]
    interruption: Dict[str, Any]
    report_digest: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "status": self.status,
            "reason": self.reason,
            "policy_errors": self.policy_errors,
            "upgrade_order": self.upgrade_order,
            "steps": self.steps,
            "availability": self.availability,
            "pdb_respected": self.pdb_respected,
            "drain_result": self.drain_result,
            "irsa_bindings": self.irsa_bindings,
            "cross_service_denied": self.cross_service_denied,
            "regulated_placement": self.regulated_placement,
            "interruption": self.interruption,
            "report_digest": self.report_digest,
        }
