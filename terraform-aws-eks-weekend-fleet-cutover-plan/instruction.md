- The weekend EKS fleet is still in design review. Build the module at /app/environment/terraform/modules/eks_weekend_fleet and give the board a real Terraform plan, not a live cluster or a hand-written plan file.

- Start from the variable and provider shell already in the module. Follow /app/environment/terraform/docs/requirements.md and the security notes beside it.

- Do not change the root module, the contract documents, /app/environment/terraform/weekend-fleet.auto.tfvars.json, or anything under /app/environment/terraform/charts.

- Work offline with the vendored providers. There are no AWS credentials or live API calls. Build ARNs from the inventory and the required naming.

- Plan a private-only control plane on the listed version and subnets, with the required log types and control-plane log group.

- Run /app/environment/scripts/render-eks-weekend-plan to create /app/output/eks_weekend_fleet_plan.json from terraform show -json. Plan fresh managed resources in the fleet module. Do not use data sources, imports, remote state, or local_file workarounds.

- Create one managed node group for each inventory entry. Carry its AMI, capacity, scaling, labels, and shared role, and add the cluster-autoscaler discovery tags. Put the required cluster tags on every resource that supports them.

- Wire cluster and node IAM as documented, including the instance profile and scoped node log-delivery policy. Do not grant broad log access.

- Build the IRSA roles with the trust and permissions from the security notes. Add-ons and Helm releases that use an identity must point to the same composed role ARN, and the outputs must agree.

- Plan every inventory add-on at its pinned version. Attach a service-account role only when the inventory names one.

- Plan every inventory Helm release from its vendored chart and apply its set_values. Releases with IRSA need the service-account wiring. An empty irsa_role means no role-ARN annotation. Keep all Helm values visible for review, with no sensitive or hidden value channels.

- Run Trivy as a node-scanner DaemonSet on every worker, with Node mode, an all-node toleration, no nodeSelector, and no IRSA.

- Add the Artifactory credential-helper DaemonSet. Refer to the existing secret by name and key only. Do not create the secret or expose its credential as a literal in configuration or plan output.

- Add one CPU alarm per node group and one for the fleet. Create the Friday park and Monday restore schedules, changing only groups marked weekend_parked.

- Plan the ALB ingress class and placeholder ingress on the required host and path.

- Export the five root outputs for cluster name, node group names, IRSA role ARNs, weekend schedule names, and monitoring alarm names. Values must be sorted, known at plan time, and derived from planned resources.

- After rendering the plan, run /app/environment/scripts/simulate-eks-weekend-cutover. It must write /app/output/eks_weekend_cutover_timeline.json from the synthetic fleet, showing Friday park followed by Monday restore, with only parked groups changing and every required invariant passing.

- The requirements and security notes define naming, tags, IAM boundaries, Helm wiring, schedules, ingress, outputs, and simulation rules. Follow them without editing the documents to excuse an incomplete module.
