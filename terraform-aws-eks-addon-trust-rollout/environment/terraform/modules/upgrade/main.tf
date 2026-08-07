# Intentionally broken starter: node-admin style trust, wrong addon pins,
# missing system taint, spot regulated capacity, unprotected node groups.

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.70"
    }
  }
}

variable "cluster_snapshot" { type = any }
variable "compatibility_matrix" { type = any }
variable "trust_observations" { type = any }
variable "regulated_policy" { type = any }
variable "defaults" { type = any }

locals {
  oidc_host = var.defaults.oidc_issuer_host
  oidc_arn  = var.defaults.oidc_provider_arn
  cluster   = var.defaults.cluster_name
  subnets   = var.defaults.private_subnet_ids
  node_role = var.defaults.node_role_arn
}

resource "aws_iam_role" "ebs_csi" {
  name = "regulated-ebs-csi"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = { Federated = local.oidc_arn }
      Action = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "${local.oidc_host}:sub" = "system:nodes"
          "${local.oidc_host}:aud" = "sts.amazonaws.com"
        }
      }
    }]
  })
  tags = {
    AddonTrust = "ebs_csi"
    Name       = "regulated-ebs-csi"
  }

  inline_policy {
    name = "ebs-admin"
    policy = jsonencode({
      Version = "2012-10-17"
      Statement = [{
        Effect   = "Allow"
        Action   = "*"
        Resource = "*"
      }]
    })
  }
}

resource "aws_iam_role" "load_balancer" {
  name = "regulated-lbc"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = { Federated = local.oidc_arn }
      Action = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "${local.oidc_host}:sub" = "system:serviceaccount:kube-system:ebs-csi-controller-sa"
          "${local.oidc_host}:aud" = "sts.amazonaws.com"
        }
      }
    }]
  })
  tags = {
    AddonTrust = "load_balancer"
    Name       = "regulated-lbc"
  }

  inline_policy {
    name = "lbc-broad"
    policy = jsonencode({
      Version = "2012-10-17"
      Statement = [{
        Effect   = "Allow"
        Action   = "iam:*"
        Resource = "*"
      }]
    })
  }
}

resource "aws_iam_role" "karpenter" {
  name = "regulated-karpenter"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = { Federated = local.oidc_arn }
      Action = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "${local.oidc_host}:sub" = "system:serviceaccount:kube-system:ebs-csi-controller-sa"
          "${local.oidc_host}:aud" = "sts.amazonaws.com"
        }
      }
    }]
  })
  tags = {
    AddonTrust = "karpenter"
    Name       = "regulated-karpenter"
  }

  inline_policy {
    name = "karpenter-broad"
    policy = jsonencode({
      Version = "2012-10-17"
      Statement = [{
        Effect   = "Allow"
        Action   = "*"
        Resource = "*"
      }]
    })
  }
}

resource "aws_eks_addon" "core" {
  for_each = {
    "vpc-cni"              = "v1.16.0-eksbuild.1"
    "kube-proxy"           = "v1.29.0-eksbuild.1"
    "coredns"              = "v1.11.1-eksbuild.4"
    "aws-ebs-csi-driver"   = "v1.31.0-eksbuild.1"
  }

  cluster_name                = local.cluster
  addon_name                  = each.key
  addon_version               = each.value
  resolve_conflicts_on_update = "OVERWRITE"

  tags = {
    AddonName = each.key
  }
}

resource "aws_ssm_parameter" "controllers" {
  for_each = {
    "aws-load-balancer-controller" = "v2.7.1"
    "karpenter"                    = "0.36.0"
  }

  name  = "/eks/${local.cluster}/controllers/${each.key}"
  type  = "String"
  value = each.value
  tags = {
    ControllerAddon = each.key
    AddonVersion    = each.value
  }
}

resource "aws_eks_node_group" "pools" {
  for_each = toset(["system", "apps", "batch"])

  cluster_name    = local.cluster
  node_group_name = each.key
  node_role_arn   = local.node_role
  subnet_ids      = local.subnets

  scaling_config {
    desired_size = 2
    max_size     = 4
    min_size     = 1
  }

  labels = {
    nodepool = each.key
  }

  tags = {
    NodePool = each.key
  }
}

resource "aws_ssm_parameter" "regulated_nodepool" {
  name  = "/eks/${local.cluster}/nodepools/regulated-on-demand"
  type  = "String"
  value = jsonencode({ capacity_types = ["on-demand", "spot"], private_only = false })
  tags = {
    Component          = "regulated-nodepool"
    RegulatedNodePool  = "true"
    NodePoolName       = "regulated-on-demand"
    CapacityTypes      = "on-demand,spot"
    PrivateSubnetsOnly = "false"
  }
}

output "addon_versions" {
  value = { for k, v in aws_eks_addon.core : k => v.addon_version }
}

output "irsa_role_arns" {
  value = {
    ebs_csi       = aws_iam_role.ebs_csi.arn
    load_balancer = aws_iam_role.load_balancer.arn
    karpenter     = aws_iam_role.karpenter.arn
  }
}
