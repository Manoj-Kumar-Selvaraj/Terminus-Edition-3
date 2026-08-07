resource "aws_eks_node_group" "this" {
  for_each = var.node_groups

  cluster_name    = aws_eks_cluster.this.name
  node_group_name = each.key
  node_role_arn   = local.node_role_arn
  subnet_ids      = var.private_subnet_ids

  capacity_type   = each.value.capacity_type
  ami_type        = each.value.ami_type
  release_version = each.value.release_version
  instance_types  = each.value.instance_types
  disk_size       = each.value.disk_size_gb
  labels          = each.value.labels

  scaling_config {
    min_size     = each.value.min_size
    desired_size = each.value.desired_size
    max_size     = each.value.max_size
  }

  update_config {
    max_unavailable = each.value.max_unavailable
  }

  tags = merge(local.aws_tags, local.autoscaler_discovery_tags)

  depends_on = [
    aws_iam_instance_profile.node,
    aws_iam_role_policy_attachment.node,
  ]
}
