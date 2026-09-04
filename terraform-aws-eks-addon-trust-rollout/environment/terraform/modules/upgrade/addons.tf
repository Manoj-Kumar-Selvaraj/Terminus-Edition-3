# EKS add-on configuration and SSM parameters for controller add-ons.
# These inventory markers are parsed by the upgrade lab plan normalizer when
# ControllerAddon / AddonName tags are present on the planned resources.

locals {
  addon_inventory = {
    "vpc-cni" = {
      target              = try(var.compatibility_matrix.addons["vpc-cni"].target, "v1.18.1-eksbuild.1")
      resolve_conflicts   = try(var.defaults.resolve_conflicts_on_update, "PRESERVE")
      kind                = "eks_addon"
    }
    "kube-proxy" = {
      target              = try(var.compatibility_matrix.addons["kube-proxy"].target, "v1.29.3-eksbuild.2")
      resolve_conflicts   = try(var.defaults.resolve_conflicts_on_update, "PRESERVE")
      kind                = "eks_addon"
    }
    "coredns" = {
      target              = try(var.compatibility_matrix.addons["coredns"].target, "v1.11.3-eksbuild.1")
      resolve_conflicts   = try(var.defaults.resolve_conflicts_on_update, "PRESERVE")
      kind                = "eks_addon"
    }
    "aws-ebs-csi-driver" = {
      target              = try(var.compatibility_matrix.addons["aws-ebs-csi-driver"].target, "v1.31.0-eksbuild.1")
      resolve_conflicts   = try(var.defaults.resolve_conflicts_on_update, "PRESERVE")
      kind                = "eks_addon"
    }
  }

  controller_inventory = {
    "aws-load-balancer-controller" = {
      target = try(var.compatibility_matrix.addons["aws-load-balancer-controller"].target, "v2.8.1")
    }
    "karpenter" = {
      target = try(var.compatibility_matrix.addons["karpenter"].target, "0.37.0")
    }
  }
}

resource "aws_ssm_parameter" "addon_versions" {
  for_each = local.addon_inventory

  name  = "/eks/${local.cluster}/addons/${each.key}/target-version"
  type  = "String"
  value = each.value.target

  tags = {
    AddonName        = each.key
    AddonKind        = each.value.kind
    ResolveConflicts = each.value.resolve_conflicts
    Component        = "addon-inventory"
  }
}

resource "aws_ssm_parameter" "addon_prereq_order" {
  for_each = var.compatibility_matrix.addons

  name = "/eks/${local.cluster}/addons/${each.key}/order"
  type = "String"
  value = jsonencode({
    order    = try(each.value.order, 0)
    requires = try(each.value.requires, [])
    kind     = try(each.value.kind, "eks_addon")
    target   = try(each.value.target, "")
  })

  tags = {
    AddonName = each.key
    Component = "addon-order"
  }
}

resource "aws_ssm_parameter" "controller_rollout_flags" {
  for_each = local.controller_inventory

  name  = "/eks/${local.cluster}/controllers/${each.key}/rollout-flags"
  type  = "String"
  value = jsonencode({
    preserve_conflicts = true
    require_irsa       = true
    target             = each.value.target
  })

  tags = {
    Component = "controller-flags"
    AddonName = each.key
  }
}
