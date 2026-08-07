# Intentionally broken starter: shared home claim, node-admin IRSA,
# undersized node group, missing taint, public-style plugin generation.

variable "fleet_registry" { type = any }
variable "node_topology" { type = any }
variable "defaults" { type = any }
variable "plugin_catalog" { type = any }

locals {
  oidc_host = var.defaults.oidc_issuer_host
  oidc_arn  = var.defaults.oidc_provider_arn
  cells     = var.fleet_registry.cells
  namespace = var.defaults.namespace
}

resource "aws_eks_node_group" "controllers" {
  cluster_name    = var.defaults.cluster_name
  node_group_name = "general"
  node_role_arn   = var.defaults.node_role_arn
  subnet_ids      = var.defaults.private_subnet_ids

  scaling_config {
    desired_size = 1
    max_size     = 2
    min_size     = 1
  }

  labels = {
    workload = "general"
  }

  tags = {
    Component = "jenkins-controllers"
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
          "${local.oidc_host}:sub" = "system:nodes"
          "${local.oidc_host}:aud" = "sts.amazonaws.com"
        }
      }
    }]
  })

  tags = {
    CellId      = each.key
    CellRole    = "controller"
    HomeClaim   = "shared-jenkins-home"
    PluginGen   = "gen-1"
    MaxUnavail  = "2"
    RoutingKey  = "shared"
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
    path = "/jenkins-home"
    creation_info {
      owner_gid   = 1000
      owner_uid   = 1000
      permissions = "755"
    }
  }

  tags = {
    CellId    = each.key
    HomeClaim = "shared-jenkins-home"
    Name      = "shared-jenkins-home"
  }
}

resource "aws_ssm_parameter" "cell" {
  for_each = local.cells

  name  = "/jenkins/cells/${each.key}/config"
  type  = "String"
  value = jsonencode({
    cell_id            = each.key
    service_account    = each.value.service_account
    home_claim         = "shared-jenkins-home"
    plugin_generation  = "gen-1"
    routing_key        = "shared"
    max_unavailable    = 2
    plugin_source      = "public-update-center"
  })

  tags = {
    CellId     = each.key
    HomeClaim  = "shared-jenkins-home"
    PluginGen  = "gen-1"
    MaxUnavail = "2"
    RoutingKey = "shared"
  }
}
