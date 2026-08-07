check "waf_enforce_before_dns" {
  assert {
    condition     = var.waf_mode == "enforce"
    error_message = "dns_cutover refuses to proceed unless waf_mode is enforce."
  }
}

check "final_canary_wired" {
  assert {
    condition     = length(var.final_canary_step_id) > 0
    error_message = "dns_cutover requires final_canary_step_id from canary_route."
  }
}

resource "local_file" "dns_payload" {
  filename        = local.payload_path
  content         = jsonencode(local.body)
  file_permission = "0644"
}

resource "null_resource" "put_dns" {
  triggers = {
    marker               = local.marker
    payload              = local_file.dns_payload.content_sha256
    engagement           = var.engagement
    base_url             = var.base_url
    zone                 = var.zone
    name                 = var.name
    target_pool          = var.target_pool
    final_canary_step_id = var.final_canary_step_id
    waf_mode             = var.waf_mode
    tls_fingerprint      = var.tls_fingerprint
  }

  provisioner "local-exec" {
    interpreter = ["/bin/bash", "-c"]
    command     = <<-EOT
      set -euo pipefail
      mkdir -p "$(dirname '${local.payload_path}')"
      "${var.edgectl_put_bin}" dns "${local.payload_path}"
    EOT
  }

  depends_on = [local_file.dns_payload]
}
