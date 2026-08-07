locals {
  fqdn = "${var.name}.${var.zone}"

  body = {
    zone                  = var.zone
    name                  = var.name
    target_pool           = var.target_pool
    require_canary_weight = var.require_canary_weight
    require_waf_enforce   = var.require_waf_enforce
  }

  marker       = sha256(jsonencode(local.body))
  payload_path = "${var.payload_dir}/${var.zone}-${var.name}.json"

  preflight = {
    final_canary_step_id = var.final_canary_step_id
    waf_mode             = var.waf_mode
    tls_fingerprint      = var.tls_fingerprint
    require_waf_enforce  = var.require_waf_enforce
    require_weight       = var.require_canary_weight
  }

  cutover_notes = [
    "DNS may flip to green only when canary weight is exactly 100.",
    "WAF must already be in enforce mode.",
    "TLS material for the edge hostname must exist.",
    "target_pool must be the healthy green pool.",
    "Engagement ${var.engagement} owns ${local.fqdn} for this window.",
  ]

  rollback = {
    previous_pool_hint = "blue"
    steps = [
      "PUT DNS back to blue only after stopping canary advances.",
      "Reduce canary weight along the reverse of canary_steps if needed.",
      "Page the engagement owner before leaving split-brain DNS.",
    ]
  }
}
