# EKS node pool configuration and taint definitions

resource "aws_ssm_parameter" "nodepool_configs" {
  for_each = {
    "system" = jsonencode({ taint = "CriticalAddonsOnly=true:NoSchedule", protected = true })
    "apps"   = jsonencode({ taint = "", protected = true })
    "batch"  = jsonencode({ taint = "", protected = true })
  }

  name  = "/eks/${local.cluster}/nodepools/${each.key}/config"
  type  = "String"
  value = each.value

  tags = {
    NodePool         = each.key
    UpgradeProtected = "true"
  }
}
