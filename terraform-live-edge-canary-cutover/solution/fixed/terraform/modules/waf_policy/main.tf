check "inventory_rule_parity" {
  assert {
    condition = alltrue([
      for r in var.waf.rules : contains(keys(local.rule_catalog), r.id)
    ])
    error_message = "every inventory waf rule id must exist in the module rule_catalog."
  }
}

resource "local_file" "waf_payload" {
  filename        = local.payload_path
  content         = jsonencode(local.body)
  file_permission = "0644"
}

resource "null_resource" "put_waf" {
  triggers = {
    marker     = local.marker
    payload    = local_file.waf_payload.content_sha256
    engagement = var.engagement
    base_url   = var.base_url
    waf_id     = var.waf.id
    mode       = var.final_mode
    rule_count = tostring(length(local.api_rules))
  }

  provisioner "local-exec" {
    interpreter = ["/bin/bash", "-c"]
    command     = <<-EOT
      set -euo pipefail
      mkdir -p "$(dirname '${local.payload_path}')"
      "${var.edgectl_put_bin}" waf "${local.payload_path}"
    EOT
  }

  depends_on = [local_file.waf_payload]
}
