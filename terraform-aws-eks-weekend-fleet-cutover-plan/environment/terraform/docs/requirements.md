# Weekend fleet control plane — schema and planned state

Owner: Platform Infrastructure
Status: binding for release 2026.07

Planned resource shapes, naming, IAM envelopes and outputs for the weekend
fleet review. Permission envelopes that already cleared security review live in
`security-review-notes.md` beside this file. What to deliver is stated in the
task prompt (`instruction.md`). The module under `modules/eks_weekend_fleet` is
implemented against this document — it does not ship the planned resources.

## 0. Planning constraints

The plan is produced on an isolated build host.

- No provider or resource may perform a remote lookup. The configuration
  contains no `data` blocks, no `import` blocks and no remote state.
- Every attribute the review board reads must be fully known at plan time.
  Where one resource needs another resource's ARN, the ARN is composed from
  `account_id` and the naming convention below rather than read back off the
  dependency. Partition is always `aws`.
- Helm charts are consumed from the vendored copies under `charts/`. No release
  may declare a chart repository.
- The inventory `weekend-fleet.auto.tfvars.json` is the single source of truth
  for sizes, versions, flags, cron expressions and identifiers. Values that
  appear there are used verbatim; nothing inventory-owned is re-derived or
  re-hardcoded.

## 1. Naming and tagging

| Object | Name |
|--------|------|
| Cluster IAM role | `<resource_prefix>-eks-cluster` |
| Node IAM role | `<resource_prefix>-eks-node` |
| Node instance profile | `<resource_prefix>-eks-node` |
| Node inline policy | `<resource_prefix>-eks-node-cluster-logs` |
| IRSA role for identity `<k>` | `<resource_prefix>-irsa-<k>` |
| IRSA inline policy for identity `<k>` | `<resource_prefix>-irsa-<k>-inline` |
| Control plane log group | `/aws/eks/<cluster_name>/cluster` |
| Per-node-group CPU alarm | `<resource_prefix>-<node group>-node-cpu` |
| Fleet-wide CPU alarm | `<resource_prefix>-cluster-node-cpu` |
| Friday schedule | `<resource_prefix>-weekend-scale-down` |
| Monday schedule | `<resource_prefix>-weekend-scale-up` |

Every taggable AWS resource carries the inventory `tags` map plus
`wfleet.io/cluster = <cluster_name>`. Node groups additionally carry the
cluster-autoscaler discovery pair `k8s.io/cluster-autoscaler/enabled = "true"`
and `k8s.io/cluster-autoscaler/<cluster_name> = "owned"`.

Managed node groups, add-ons and Helm releases are named by their inventory
keys.

## 2. Control plane

The API server endpoint is VPC-private only. The cluster runs the inventory
Kubernetes version in the inventory private subnets, attached to the
pre-provisioned control plane security group.

Exactly the inventory `cluster_log_types` are enabled. The control plane log
group named above exists with the inventory retention.

## 3. Managed node groups

One managed node group per inventory entry, in every private subnet, using the
node IAM role ARN. Capacity type, AMI type, AMI release version, instance type
list, root disk size, Kubernetes labels, scaling bounds and
`max_unavailable` all come from that entry.

## 4. Cluster and node IAM

The cluster role is assumable by `eks.amazonaws.com` and the node role by
`ec2.amazonaws.com`, both through `sts:AssumeRole`.

Attached AWS managed policies:

| Role | Policies |
|------|----------|
| Cluster | `AmazonEKSClusterPolicy`, `AmazonEKSVPCResourceController` |
| Node | `AmazonEC2ContainerRegistryReadOnly`, `AmazonEKSWorkerNodePolicy`, `AmazonEKS_CNI_Policy`, `AmazonSSMManagedInstanceCore` |

Nodes join through an instance profile that wraps the node role.

The node role also carries one inline policy holding a single statement with
Sid `ScopedClusterLogDelivery`: `logs:CreateLogStream`,
`logs:DescribeLogStreams` and `logs:PutLogEvents`, allowed only on
`arn:aws:logs:<region>:<account_id>:log-group:/aws/eks/<cluster_name>/cluster:*`.
Blanket log access is a review-board rejection.

## 5. Core add-ons

One add-on per inventory entry, at the pinned version, with
`resolve_conflicts_on_create = OVERWRITE` and
`resolve_conflicts_on_update` taken from the inventory. An entry whose
`irsa_role` is non-empty runs under the corresponding IRSA role ARN; an empty
`irsa_role` attaches no service account role.

## 6. Workload identity

One IAM role per `irsa_roles` entry. Trust and inline policy shape are defined
in `security-review-notes.md`. Dropping either OIDC condition key, loosening
the subject to a wildcard, or granting actions outside the closed envelopes
fails review.

The same composed IRSA role ARN is what add-ons and Helm releases that name
that identity must reference — three places, one ARN.

## 7. Helm releases

One release per inventory entry, from `charts/<chart_dir>`, without creating
namespaces. Service-account wiring and controller-specific values are defined
in `security-review-notes.md`. Inventory `set_values` are applied verbatim and
must not be replaced by chart defaults.

A release whose `irsa_role` is non-empty receives the IRSA service-account
wiring from the security notes. An empty `irsa_role` creates a service account
without a role-arn annotation.

### 7.1 Trivy node scanner

The inventory `trivy` release installs Trivy as a **DaemonSet on every worker
node** (every managed node group). The release carries no IRSA identity. Its
inventory `set_values` must be applied verbatim and include:

| Key | Value |
|-----|-------|
| `workloadKind` | `DaemonSet` |
| `trivy.mode` | `Node` |
| `serviceAccount.name` | `trivy` |
| `tolerations[0].operator` | `Exists` |
| `tolerations[0].effect` | `` (empty — tolerate every effect) |

The release must not set a `nodeSelector` (no key under `nodeSelector.*` in
`set_values`) so scheduling is not limited to a single node pool. The
`Exists` toleration is what lets the scanner land on both on-demand and spot
workers, including any taints those pools carry.

## 8. Artifactory credential helper

A DaemonSet named by the inventory, in the inventory namespace, running the
inventory helper image. Pods pull through the pre-provisioned image pull
secret by name only — this module never creates that secret.

| Variable | Source |
|----------|--------|
| `ARTIFACTORY_REGISTRY_URL` | literal registry host |
| `ARTIFACTORY_REFRESH_INTERVAL_SECONDS` | literal refresh interval |
| `ARTIFACTORY_USERNAME` | secret key reference, username key of the pull secret |
| `ARTIFACTORY_PASSWORD` | secret key reference, password key of the pull secret |

The registry credential never appears as a literal anywhere in the
configuration or the rendered plan.

## 9. Alarms

One CPU alarm per node group plus one fleet-wide CPU alarm, all on the
inventory metric namespace and metric name, `Average` statistic,
`GreaterThanOrEqualToThreshold`, inventory period and evaluation periods, and
`breaching` treatment of missing data. Both the alarm and OK transitions
notify the inventory alarm topic.

Per-node-group alarms are dimensioned on `ClusterName` and `NodegroupName` and
use that node group's own threshold. The fleet-wide alarm is dimensioned on
`ClusterName` only and uses the inventory cluster threshold.

## 10. Weekend cutover

A schedule group named by the inventory holds exactly two EventBridge
schedules, both `ENABLED`, both in the inventory timezone, both using a
`FLEXIBLE` time window of the inventory width, and both invoking the inventory
placeholder Lambda under the inventory scheduler role.

The Friday schedule uses `scale_down_cron`; the Monday schedule uses
`scale_up_cron`. Each target payload is a JSON object:

```json
{
  "action": "scale-down | scale-up",
  "cluster_name": "<cluster_name>",
  "region": "<region>",
  "node_groups": {
    "<node group>": { "min_size": <int>, "desired_size": <int> }
  }
}
```

`node_groups` covers exactly the node groups flagged `weekend_parked` in the
inventory. Scale-down parks them at zero on both bounds; scale-up restores the
inventory `min_size` and `desired_size`. Node groups that are not flagged never
appear in either payload.

### 10.1 Cutover simulation

After the plan document is rendered, `/app/environment/scripts/simulate-eks-weekend-cutover`
steps the two schedules against a synthetic fleet seeded from the inventory and
writes `/app/output/eks_weekend_cutover_timeline.json`. The transcript must
report `ok: true` and preserve these invariants:

- Friday scale-down runs before Monday scale-up; the flexible window does not
  invert that order.
- Payload `node_groups` keys equal the `weekend_parked` set on both steps.
- After scale-down every parked group is `{min_size: 0, desired_size: 0}` and
  every non-parked group is unchanged.
- After scale-up every parked group is restored to its inventory
  `min_size`/`desired_size` and non-parked groups remain unchanged.

Do not hand-write the timeline — it must be produced by the simulator from the
real plan document.

## 11. Ingress

An ingress class named by the inventory, backed by the inventory controller,
and a placeholder ingress in the inventory namespace bound to that class. The
placeholder is annotated with `alb.ingress.kubernetes.io/scheme` and
`alb.ingress.kubernetes.io/target-type` from the inventory, and routes host
`placeholder_host` on a `Prefix` match of `/` to the inventory service name and
port.

## 12. Module outputs

The frozen root re-exports five module outputs, all known at plan time:

| Output | Type | Content |
|--------|------|---------|
| `cluster_name` | string | cluster name |
| `node_group_names` | list(string) | node group names, sorted |
| `irsa_role_arns` | map(string) | identity key to IRSA role ARN |
| `weekend_schedule_names` | list(string) | schedule names, sorted |
| `monitoring_alarm_names` | list(string) | every alarm name, sorted |

Root `main.tf`, `variables.tf`, `outputs.tf`, `providers.tf`, `versions.tf`,
this document, `security-review-notes.md`, `weekend-fleet.auto.tfvars.json`,
and `charts/` are frozen inputs to the plan.
