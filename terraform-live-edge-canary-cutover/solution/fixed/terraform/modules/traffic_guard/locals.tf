locals {
  assert_args = [
    tostring(var.max_error_rate_pct),
    tostring(var.expect_weight),
    var.expect_pool,
  ]

  guard_policy = {
    engagement         = var.engagement
    max_error_rate_pct = var.max_error_rate_pct
    expect_weight      = var.expect_weight
    expect_pool        = var.expect_pool
    dns_target_pool    = var.dns_target_pool
    base_url           = var.base_url
    enabled            = var.enabled
  }

  failure_modes = [
    "error_rate_pct exceeds max_error_rate_pct",
    "canary_weight_green is not expect_weight",
    "dns_target_pool does not equal expect_pool",
    "control plane metrics endpoint unreachable",
  ]

  remediation = [
    "Halt further canary or DNS changes.",
    "Inspect GET /v1/metrics and GET /v1/snapshot.",
    "Confirm green origins remain healthy and WAF is enforce.",
    "Re-run traffic_guard after the sliding window cools.",
  ]
}
