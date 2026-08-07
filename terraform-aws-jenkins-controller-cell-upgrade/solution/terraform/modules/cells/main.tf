variable "fleet_registry" { type = any }
variable "node_topology" { type = any }
variable "defaults" { type = any }
variable "plugin_catalog" { type = any }

locals {
  oidc_host = var.defaults.oidc_issuer_host
  oidc_arn  = var.defaults.oidc_provider_arn
  cells     = var.fleet_registry.cells
  namespace = var.defaults.namespace
  topology  = var.node_topology
}

resource "aws_eks_node_group" "controllers" {
  cluster_name    = var.defaults.cluster_name
  node_group_name = local.topology.node_group_key
  node_role_arn   = var.defaults.node_role_arn
  subnet_ids      = var.defaults.private_subnet_ids

  scaling_config {
    desired_size = local.topology.desired_size
    max_size     = local.topology.desired_size + 1
    min_size     = local.topology.min_size
  }

  labels = {
    workload  = local.topology.labels.workload
    dedicated = local.topology.labels.dedicated
  }

  taint {
    key    = local.topology.taints[0].key
    value  = local.topology.taints[0].value
    effect = local.topology.taints[0].effect
  }

  tags = {
    Component      = "jenkins-controllers"
    MaxUnavailable = tostring(local.topology.pdb.max_unavailable)
    MinAvailable   = tostring(local.topology.pdb.min_available)
  }
}

resource "aws_iam_role" "cell" {
  for_each = local.cells

  name = "jenkins-${each.key}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = local.oidc_arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "${local.oidc_host}:sub" = "system:serviceaccount:${local.namespace}:${each.value.service_account}"
          "${local.oidc_host}:aud" = "sts.amazonaws.com"
        }
      }
    }]
  })

  tags = {
    CellId     = each.key
    CellRole   = "controller"
    HomeClaim  = each.value.home_claim
    PluginGen  = each.value.plugin_generation
    MaxUnavail = tostring(local.topology.pdb.max_unavailable)
    RoutingKey = each.value.routing_key
  }
}

resource "aws_efs_access_point" "home" {
  for_each = local.cells

  file_system_id = var.defaults.efs_filesystem_id

  posix_user {
    gid = 1000
    uid = 1000
  }

  root_directory {
    path = "/homes/${each.key}"
    creation_info {
      owner_gid   = 1000
      owner_uid   = 1000
      permissions = "755"
    }
  }

  tags = {
    CellId    = each.key
    HomeClaim = each.value.home_claim
    Name      = each.value.home_claim
  }
}

resource "aws_ssm_parameter" "cell" {
  for_each = local.cells

  name  = "/jenkins/cells/${each.key}/config"
  type  = "String"
  value = jsonencode({
    cell_id           = each.key
    service_account   = each.value.service_account
    home_claim        = each.value.home_claim
    plugin_generation = each.value.plugin_generation
    routing_key       = each.value.routing_key
    max_unavailable   = local.topology.pdb.max_unavailable
    plugin_source     = var.plugin_catalog.plugin_source
    az_preference     = each.value.az_preference
  })

  tags = {
    CellId     = each.key
    HomeClaim  = each.value.home_claim
    PluginGen  = each.value.plugin_generation
    MaxUnavail = tostring(local.topology.pdb.max_unavailable)
    RoutingKey = each.value.routing_key
  }
}
