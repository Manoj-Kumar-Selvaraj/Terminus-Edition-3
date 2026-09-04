# EKS node pool configuration, protection tags, and regulated capacity markers.

locals {
  companion_pools = try(var.defaults.companion_node_pools, ["apps", "batch"])
  system_taint = try(var.defaults.system_taint, {
    key    = "CriticalAddonsOnly"
    value  = "true"
    effect = "NO_SCHEDULE"
  })
  regulated_pool = try(var.regulated_policy.nodepool, {
    name                 = "regulated-on-demand"
    capacity_types       = ["on-demand"]
    private_subnets_only = true
    discovery_tag_key    = "karpenter.sh/discovery"
  })
}

resource "aws_ssm_parameter" "nodepool_configs" {
  for_each = {
    "system" = jsonencode({
      taint     = "${local.system_taint.key}=${local.system_taint.value}:${local.system_taint.effect}"
      protected = true
      labels    = { nodepool = "system" }
    })
    "apps" = jsonencode({
      taint     = ""
      protected = true
      labels    = { nodepool = "apps" }
    })
    "batch" = jsonencode({
      taint     = ""
      protected = true
      labels    = { nodepool = "batch" }
    })
  }

  name  = "/eks/${local.cluster}/nodepools/${each.key}/config"
  type  = "String"
  value = each.value

  tags = {
    NodePool         = each.key
    UpgradeProtected = "true"
    Component        = "nodepool-config"
  }
}

resource "aws_ssm_parameter" "companion_pool_guard" {
  for_each = toset(local.companion_pools)

  name = "/eks/${local.cluster}/nodepools/${each.key}/upgrade-guard"
  type = "String"
  value = jsonencode({
    upgrade_protected = true
    nodepool_label    = each.key
    allow_replace     = false
  })

  tags = {
    NodePool         = each.key
    UpgradeProtected = "true"
    Component        = "companion-guard"
  }
}

resource "aws_ssm_parameter" "regulated_capacity_contract" {
  name = "/eks/${local.cluster}/nodepools/${local.regulated_pool.name}/contract"
  type = "String"
  value = jsonencode({
    capacity_types       = try(local.regulated_pool.capacity_types, ["on-demand"])
    private_subnets_only = try(local.regulated_pool.private_subnets_only, true)
    discovery_tag_key    = try(local.regulated_pool.discovery_tag_key, "karpenter.sh/discovery")
    workloads            = [for wl in try(var.regulated_policy.workloads, []) : wl.name]
  })

  tags = {
    Component        = "regulated-capacity-contract"
    NodePoolName     = local.regulated_pool.name
    UpgradeProtected = "true"
  }
}

resource "aws_ssm_parameter" "system_taint_contract" {
  name = "/eks/${local.cluster}/nodepools/system/taint-contract"
  type = "String"
  value = jsonencode(local.system_taint)

  tags = {
    NodePool  = "system"
    Component = "system-taint"
  }
}
