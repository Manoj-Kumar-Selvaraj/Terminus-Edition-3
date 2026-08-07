locals {
  step_count = length(var.canary_steps)

  monotonic_ok = local.step_count < 2 || alltrue([
    for i in range(1, local.step_count) : var.canary_steps[i] > var.canary_steps[i - 1]
  ])

  steps = {
    for idx, weight in var.canary_steps : format("step-%02d-%03d", idx, weight) => {
      index  = idx
      weight = weight
      body = {
        id           = var.route_id
        blue_pool    = var.blue_pool_id
        green_pool   = var.green_pool_id
        weight_green = weight
      }
      payload_path = format("%s/%s-step-%02d-%03d.json", var.payload_dir, var.route_id, idx, weight)
      marker = sha256(jsonencode({
        id           = var.route_id
        blue_pool    = var.blue_pool_id
        green_pool   = var.green_pool_id
        weight_green = weight
        engagement   = var.engagement
        index        = idx
      }))
    }
  }

  step_keys_ordered = [
    for idx, weight in var.canary_steps : format("step-%02d-%03d", idx, weight)
  ]

  final_key    = local.step_keys_ordered[local.step_count - 1]
  final_weight = var.canary_steps[local.step_count - 1]

  bake_guidance = {
    for idx, weight in var.canary_steps : format("step-%02d-%03d", idx, weight) => {
      weight            = weight
      min_bake_seconds  = weight < 50 ? 30 : (weight < 100 ? 60 : 90)
      error_budget_pct  = var.error_budget_pct
      abort_if_errors   = true
      observe_metrics   = [
        "error_rate_pct",
        "canary_weight_green",
        "requests",
        "errors",
      ]
      rollback_weight   = idx == 0 ? 0 : var.canary_steps[idx - 1]
      operator_notes = [
        "Apply weight ${weight} only after previous step is live.",
        "Refuse to advance while error_rate_pct exceeds ${var.error_budget_pct}.",
        "Pools ${var.blue_pool_id} and ${var.green_pool_id} must remain healthy.",
        "WAF ${var.waf_applied_id} and TLS ${var.tls_applied_id} must already be installed.",
      ]
    }
  }

  step_runbook = [
    "Confirm both pools healthy via GET /v1/snapshot.",
    "Confirm WAF mode enforce and TLS fingerprint match inventory.",
    "Walk canary_steps in order — never skip, never reorder.",
    "After each step, sample GET /v1/metrics until window is warm.",
    "Only after weight 100, allow dns_cutover to target green.",
  ]
}
