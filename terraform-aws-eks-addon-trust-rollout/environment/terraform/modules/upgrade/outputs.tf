# Outputs for EKS add-on trust rollout upgrade module

output "addon_versions" {
  description = "Configured EKS add-on versions"
  value       = { for k, v in aws_eks_addon.core : k => v.addon_version }
}

output "irsa_role_arns" {
  description = "ARNs of configured IRSA roles"
  value = {
    ebs_csi       = aws_iam_role.ebs_csi.arn
    load_balancer = aws_iam_role.load_balancer.arn
    karpenter     = aws_iam_role.karpenter.arn
  }
}

output "nodepool_names" {
  description = "Configured EKS node group names"
  value       = [for k, v in aws_eks_node_group.pools : v.node_group_name]
}
