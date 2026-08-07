# terraform-aws-jenkins-controller-cell-upgrade

Edition 3 migration of the Jenkins-on-EKS fleet theme into a controller-cell
isolation and upgrade incident. Graded on Terraform plan semantics plus a
filesystem Jenkins-like lab — not hand-authored run traces or resource labels.

## Novelty

Distinct from `terraform-aws-eks-addon-trust-rollout` (add-on/IRSA upgrade window)
and from claims-edge / wave-transition tasks. The center is per-cell identity,
exclusive homes, plugin provenance, job routing, and rollback without losing
builds. Fleet membership uses an explicit registry, not a fake Operations Center.

## Verification

Separate verifier re-plans submitted modules with hidden inventories, runs the
trusted cell lab (job submit, restart, failed upgrade drill), and checks
isolation invariants. Oracle reward 1 / NOP reward 0 required.
