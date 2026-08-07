terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.70"
    }
  }
}

variable "cluster_snapshot" {
  type = any
}

variable "compatibility_matrix" {
  type = any
}

variable "trust_observations" {
  type = any
}

variable "regulated_policy" {
  type = any
}

variable "defaults" {
  type = any
}

locals {
  oidc_host   = var.defaults.oidc_issuer_host
  oidc_arn    = var.defaults.oidc_provider_arn
  cluster     = var.defaults.cluster_name
  subjects    = var.trust_observations.required_subjects
  role_names  = var.trust_observations.role_names
  addons      = var.compatibility_matrix.addons
  taint       = var.defaults.system_taint
  subnets     = var.defaults.private_subnet_ids
  node_role   = var.defaults.node_role_arn
  reg_pool    = var.regulated_policy.nodepool
}

data "aws_iam_policy_document" "ebs_csi_trust" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    effect  = "Allow"
    principals {
      type        = "Federated"
      identifiers = [local.oidc_arn]
    }
    condition {
      test     = "StringEquals"
      variable = "${local.oidc_host}:sub"
      values   = [local.subjects.ebs_csi]
    }
    condition {
      test     = "StringEquals"
      variable = "${local.oidc_host}:aud"
      values   = ["sts.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "lbc_trust" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    effect  = "Allow"
    principals {
      type        = "Federated"
      identifiers = [local.oidc_arn]
    }
    condition {
      test     = "StringEquals"
      variable = "${local.oidc_host}:sub"
      values   = [local.subjects.load_balancer]
    }
    condition {
      test     = "StringEquals"
      variable = "${local.oidc_host}:aud"
      values   = ["sts.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "karpenter_trust" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    effect  = "Allow"
    principals {
      type        = "Federated"
      identifiers = [local.oidc_arn]
    }
    condition {
      test     = "StringEquals"
      variable = "${local.oidc_host}:sub"
      values   = [local.subjects.karpenter]
    }
    condition {
      test     = "StringEquals"
      variable = "${local.oidc_host}:aud"
      values   = ["sts.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ebs_csi" {
  name               = local.role_names.ebs_csi
  assume_role_policy = data.aws_iam_policy_document.ebs_csi_trust.json
  tags = {
    AddonTrust       = "ebs_csi"
    UpgradeProtected = "true"
    Name             = local.role_names.ebs_csi
  }

  inline_policy {
    name = "ebs-csi-scoped"
    policy = jsonencode({
      Version = "2012-10-17"
      Statement = [{
        Effect = "Allow"
        Action = [
          "ec2:AttachVolume",
          "ec2:CreateVolume",
          "ec2:DetachVolume",
          "ec2:DescribeVolumes",
          "ec2:CreateSnapshot",
          "ec2:DescribeSnapshots",
          "ec2:DeleteSnapshot"
        ]
        Resource = [
          "arn:aws:ec2:*:${var.defaults.account_id}:volume/*",
          "arn:aws:ec2:*:${var.defaults.account_id}:snapshot/*",
          "arn:aws:ec2:*:${var.defaults.account_id}:instance/*"
        ]
      }]
    })
  }
}

resource "aws_iam_role" "load_balancer" {
  name               = local.role_names.load_balancer
  assume_role_policy = data.aws_iam_policy_document.lbc_trust.json
  tags = {
    AddonTrust       = "load_balancer"
    UpgradeProtected = "true"
    Name             = local.role_names.load_balancer
  }

  inline_policy {
    name = "lbc-scoped"
    policy = jsonencode({
      Version = "2012-10-17"
      Statement = [{
        Effect = "Allow"
        Action = [
          "elasticloadbalancing:CreateLoadBalancer",
          "elasticloadbalancing:CreateTargetGroup",
          "elasticloadbalancing:DescribeLoadBalancers",
          "elasticloadbalancing:DescribeTargetGroups",
          "elasticloadbalancing:DescribeTargetHealth",
          "ec2:DescribeSubnets",
          "ec2:DescribeSecurityGroups",
          "ec2:DescribeVpcs",
          "acm:ListCertificates",
          "acm:DescribeCertificate",
          "iam:CreateServiceLinkedRole"
        ]
        Resource = [
          "arn:aws:elasticloadbalancing:*:${var.defaults.account_id}:*/*",
          "arn:aws:ec2:*:${var.defaults.account_id}:*/*",
          "arn:aws:acm:*:${var.defaults.account_id}:certificate/*",
          "arn:aws:iam::${var.defaults.account_id}:role/*"
        ]
      }]
    })
  }
}

resource "aws_iam_role" "karpenter" {
  name               = local.role_names.karpenter
  assume_role_policy = data.aws_iam_policy_document.karpenter_trust.json
  tags = {
    AddonTrust       = "karpenter"
    UpgradeProtected = "true"
    Name             = local.role_names.karpenter
  }

  inline_policy {
    name = "karpenter-scoped"
    policy = jsonencode({
      Version = "2012-10-17"
      Statement = [{
        Effect = "Allow"
        Action = [
          "ec2:CreateFleet",
          "ec2:CreateLaunchTemplate",
          "ec2:CreateTags",
          "ec2:DescribeInstances",
          "ec2:DescribeInstanceTypes",
          "ec2:DescribeSubnets",
          "ec2:RunInstances",
          "ec2:TerminateInstances",
          "pricing:GetProducts",
          "ssm:GetParameter",
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes",
          "iam:PassRole"
        ]
        Resource = [
          "arn:aws:ec2:*:${var.defaults.account_id}:*/*",
          "arn:aws:pricing:*::*",
          "arn:aws:ssm:*:${var.defaults.account_id}:parameter/*",
          "arn:aws:sqs:*:${var.defaults.account_id}:*",
          "arn:aws:iam::${var.defaults.account_id}:role/${var.defaults.cluster_name}-*"
        ]
      }]
    })
  }
}

resource "aws_eks_addon" "core" {
  for_each = {
    for name, meta in local.addons : name => meta if meta.kind == "eks_addon"
  }

  cluster_name                = local.cluster
  addon_name                  = each.key
  addon_version               = each.value.target
  resolve_conflicts_on_update = var.defaults.resolve_conflicts_on_update
  service_account_role_arn = try(
    {
      "aws-ebs-csi-driver" = aws_iam_role.ebs_csi.arn
    }[each.key],
    null
  )

  tags = {
    AddonName        = each.key
    UpgradeProtected = "true"
  }
}

resource "aws_ssm_parameter" "controllers" {
  for_each = {
    for name, meta in local.addons : name => meta if meta.kind == "controller"
  }

  name  = "/eks/${local.cluster}/controllers/${each.key}"
  type  = "String"
  value = each.value.target
  tags = {
    ControllerAddon  = each.key
    AddonVersion     = each.value.target
    ResolveConflicts = var.defaults.resolve_conflicts_on_update
    UpgradeProtected = "true"
  }
}

resource "aws_eks_node_group" "pools" {
  for_each = {
    system = {
      labels = { nodepool = "system" }
      taints = [{
        key    = local.taint.key
        value  = local.taint.value
        effect = local.taint.effect
      }]
    }
    apps = {
      labels = { nodepool = "apps" }
      taints = []
    }
    batch = {
      labels = { nodepool = "batch" }
      taints = []
    }
  }

  cluster_name    = local.cluster
  node_group_name = each.key
  node_role_arn   = local.node_role
  subnet_ids      = local.subnets

  scaling_config {
    desired_size = each.key == "apps" ? 3 : (each.key == "system" ? 2 : 1)
    max_size     = each.key == "apps" ? 6 : 4
    min_size     = each.key == "batch" ? 0 : 2
  }

  labels = each.value.labels

  dynamic "taint" {
    for_each = each.value.taints
    content {
      key    = taint.value.key
      value  = taint.value.value
      effect = taint.value.effect
    }
  }

  tags = {
    NodePool         = each.key
    UpgradeProtected = "true"
  }
}

resource "aws_ssm_parameter" "regulated_nodepool" {
  name = "/eks/${local.cluster}/nodepools/${local.reg_pool.name}"
  type = "String"
  value = jsonencode({
    capacity_types = local.reg_pool.capacity_types
    private_only   = local.reg_pool.private_subnets_only
  })
  tags = {
    Component          = "regulated-nodepool"
    RegulatedNodePool  = "true"
    NodePoolName       = local.reg_pool.name
    CapacityTypes      = join(",", local.reg_pool.capacity_types)
    PrivateSubnetsOnly = tostring(local.reg_pool.private_subnets_only)
    UpgradeProtected   = "true"
  }
}

output "addon_versions" {
  value = {
    for name, meta in local.addons : name => meta.target
  }
}

output "irsa_role_arns" {
  value = {
    ebs_csi       = aws_iam_role.ebs_csi.arn
    load_balancer = aws_iam_role.load_balancer.arn
    karpenter     = aws_iam_role.karpenter.arn
  }
}
