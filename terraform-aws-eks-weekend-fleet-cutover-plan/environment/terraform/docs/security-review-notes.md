# Security review notes — weekend fleet IRSA and Helm

Status: approved envelopes for release 2026.07 (read with the planned-state
document beside this file).
These notes are not a walkthrough; they record what security already signed.

## IRSA trust shape

Every workload identity role carries exactly one trust statement:

- Sid: `WeekendFleetWebIdentity`
- Action: `sts:AssumeRoleWithWebIdentity`
- Principal: the inventory OIDC provider ARN
- `StringEquals` condition on **both**:
  - `<oidc_provider_url>:aud` = `sts.amazonaws.com`
  - `<oidc_provider_url>:sub` = `system:serviceaccount:<namespace>:<service account>`

A missing audience key, a missing subject key, or a wildcard subject fails
review.

Each role carries exactly one inline policy with exactly two statements:

- Sid `Discovery` — read-only actions, `Resource` `*`, no condition.
- Sid `ScopedMutation` — mutating actions, `Resource` `*`, gated by a
  `StringEquals` condition that pins the target to this cluster.

Anything beyond the closed action sets below is over-privilege.

### `ebs-csi`

Condition: `aws:ResourceTag/kubernetes.io/cluster/<cluster_name>` = `owned`

| Statement | Actions |
|-----------|---------|
| Discovery | `ec2:DescribeAvailabilityZones`, `ec2:DescribeInstances`, `ec2:DescribeSnapshots`, `ec2:DescribeTags`, `ec2:DescribeVolumes`, `ec2:DescribeVolumesModifications` |
| ScopedMutation | `ec2:AttachVolume`, `ec2:CreateSnapshot`, `ec2:CreateTags`, `ec2:DeleteSnapshot`, `ec2:DeleteVolume`, `ec2:DetachVolume`, `ec2:ModifyVolume` |

### `cluster-autoscaler`

Condition: `autoscaling:ResourceTag/kubernetes.io/cluster/<cluster_name>` = `owned`

| Statement | Actions |
|-----------|---------|
| Discovery | `autoscaling:DescribeAutoScalingGroups`, `autoscaling:DescribeAutoScalingInstances`, `autoscaling:DescribeLaunchConfigurations`, `autoscaling:DescribeScalingActivities`, `autoscaling:DescribeTags`, `ec2:DescribeInstanceTypes`, `ec2:DescribeLaunchTemplateVersions`, `eks:DescribeNodegroup` |
| ScopedMutation | `autoscaling:SetDesiredCapacity`, `autoscaling:TerminateInstanceInAutoScalingGroup`, `autoscaling:UpdateAutoScalingGroup` |

### `aws-load-balancer-controller`

Condition: `elasticloadbalancing:ResourceTag/elbv2.k8s.aws/cluster` = `<cluster_name>`

| Statement | Actions |
|-----------|---------|
| Discovery | `ec2:DescribeAvailabilityZones`, `ec2:DescribeSecurityGroups`, `ec2:DescribeSubnets`, `ec2:DescribeVpcs`, `elasticloadbalancing:DescribeListeners`, `elasticloadbalancing:DescribeLoadBalancers`, `elasticloadbalancing:DescribeTargetGroups`, `elasticloadbalancing:DescribeTargetHealth` |
| ScopedMutation | `elasticloadbalancing:AddTags`, `elasticloadbalancing:DeleteLoadBalancer`, `elasticloadbalancing:DeleteTargetGroup`, `elasticloadbalancing:DeregisterTargets`, `elasticloadbalancing:ModifyListener`, `elasticloadbalancing:ModifyTargetGroup`, `elasticloadbalancing:RegisterTargets` |

## Helm service-account wiring

Every release receives its inventory `set_values` verbatim, plus
`serviceAccount.create = true`.

When the release's `irsa_role` is non-empty, also set:

| Key | Value |
|-----|-------|
| `serviceAccount.name` | service account of the release's IRSA identity |
| `serviceAccount.annotations.eks\.amazonaws\.com/role-arn` | ARN of the release's IRSA role |

When `irsa_role` is empty (for example the `trivy` node scanner), do **not**
set a role-arn annotation. The service account name comes from the inventory
`set_values` (`serviceAccount.name`).

The `aws-load-balancer-controller` release additionally receives `clusterName`,
`region` and `vpcId` from the inventory cluster fields (not from chart
discovery), because the vendored chart cannot discover them without an API
server.

Where a release carries an IRSA identity, the role ARN written into the Helm
annotation must be identical to the ARN attached to any add-on that names the
same identity.
