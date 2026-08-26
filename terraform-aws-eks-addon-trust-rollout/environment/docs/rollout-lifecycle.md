# EKS Add-on Rollout Lifecycle & Order Contract

Add-on controllers must be upgraded in a strict sequence determined by dependency prerequisites in `/app/data/compatibility_matrix.json`.

## Upgrade Sequence

1. **vpc-cni** (Order 1): Network plugin prerequisite for all pod networking.
2. **kube-proxy** (Order 2): Service proxy required for internal service routing.
3. **coredns** (Order 3): Cluster DNS resolution required for controller service discovery.
4. **aws-ebs-csi-driver** (Order 4): Storage driver for persistent volumes.
5. **aws-load-balancer-controller** (Order 5): Ingress and service load balancing controller.
6. **karpenter** (Order 6): Autoscaling and node provisioning controller.

## Step Validation Rules

- Every step checks that all prerequisite add-ons are in `ACTIVE` status before proceeding.
- If a prerequisite is missing or not active, rollout stops immediately with `prerequisite_missing:<addon_name>`.
- Readiness is verified before marking a step as completed (`ok: true`).
