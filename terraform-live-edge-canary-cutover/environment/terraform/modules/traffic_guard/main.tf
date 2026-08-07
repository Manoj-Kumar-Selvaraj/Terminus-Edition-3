check "dns_pool_alignment" {
  assert {
    condition     = var.dns_target_pool == var.expect_pool
    error_message = "traffic_guard expect_pool must equal dns_cutover target_pool."
  }
}

check "observatory_present" {
  assert {
    condition     = var.observatory_ready >= 1
    error_message = "traffic_guard requires observatory probes to be materialized."
  }
}

resource "null_resource" "metrics_assert" {
  count = var.enabled ? 1 : 0

  triggers = {
    engagement         = var.engagement
    max_error_rate_pct = tostring(var.max_error_rate_pct)
    expect_weight      = tostring(var.expect_weight)
    expect_pool        = var.expect_pool
    dns_target_pool    = var.dns_target_pool
    observatory_ready  = tostring(var.observatory_ready)
    base_url           = var.base_url
    # force re-evaluate on each apply
    nonce              = timestamp()
  }

  provisioner "local-exec" {
    interpreter = ["/bin/bash", "-c"]
    command     = <<-EOT
      set -euo pipefail
      "${var.edgectl_put_bin}" metrics-assert ${var.max_error_rate_pct} ${var.expect_weight} "${var.expect_pool}"
    EOT
  }

  lifecycle {
    ignore_changes = []
  }
}
