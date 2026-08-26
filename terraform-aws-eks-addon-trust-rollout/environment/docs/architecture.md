# EKS Add-on Trust Upgrade Lab Architecture

The EKS add-on trust upgrade lab models a production-grade EKS cluster upgrade control plane.

## Key Subsystems

1. **Terraform Upgrade Workspace (`/app/terraform/workspaces/upgrade`)**:
   - Manages EKS add-ons (`vpc-cni`, `kube-proxy`, `coredns`, `aws-ebs-csi-driver`).
   - Configures IAM Roles for Service Accounts (IRSA) for `ebs_csi`, `load_balancer`, and `karpenter`.
   - Defines system and application node groups with taints, labels, and protection tags.

2. **Kubernetes Manifest Plane (`/app/k8s`)**:
   - PodDisruptionBudgets (PDBs) for core system controllers.
   - Service Accounts with `eks.amazonaws.com/role-arn` annotations.
   - Regulated workload deployments (`payment-authorizer`, `settlement-reconciler`) with strict `nodeSelector` and `karpenter.sh/capacity-type` constraints.
   - Karpenter `NodePool` and `EC2NodeClass` CRD manifests.

3. **Upgrade Lab Engine (`/app/upgrade_lab`)**:
   - Plan Normalizer & Policy Validator: Parses `terraform show -json` output and enforces version, conflict, taint, and protection policies.
   - IRSA Verifier: Enforces single-subject service account trust and cross-service isolation.
   - PDB & Drain Simulator: Models system node drains while respecting PDB `minAvailable` budgets.
   - Placement & Interruption Simulator: Validates regulated workload capacity placement under rebalancing events.
   - Rollout State Machine: Coordinates step-by-step add-on upgrades in compatibility matrix order.
   - Report Publisher: Computes canonical SHA-256 digests over stable report fields.

4. **Public Operator CLI (`/app/bin/addon-trust-rollout`)**:
   - Runs Terraform plan, invokes rollout coordinator, and generates `/app/output/upgrade-report.json` and `/app/var/upgrade/plan.json`.
