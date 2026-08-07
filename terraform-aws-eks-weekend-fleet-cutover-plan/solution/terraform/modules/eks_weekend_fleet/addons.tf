resource "aws_eks_addon" "this" {
  for_each = var.cluster_addons

  cluster_name = aws_eks_cluster.this.name
  addon_name   = each.key

  addon_version               = each.value.addon_version
  resolve_conflicts_on_create = "OVERWRITE"
  resolve_conflicts_on_update = each.value.resolve_conflicts_on_update
  service_account_role_arn    = each.value.irsa_role == "" ? null : local.irsa_role_arns[each.value.irsa_role]

  tags = local.aws_tags

  depends_on = [
    aws_eks_node_group.this,
    aws_iam_role_policy.irsa,
  ]
}
