resource "local_file" "tls_payload" {
  filename        = local.payload_path
  content         = jsonencode(local.body)
  file_permission = "0644"
}

resource "null_resource" "put_tls" {
  triggers = {
    marker      = local.marker
    payload     = local_file.tls_payload.content_sha256
    engagement  = var.engagement
    base_url    = var.base_url
    tls_id      = var.tls_id
    hostname    = var.hostname
    fingerprint = var.fingerprint
  }

  provisioner "local-exec" {
    interpreter = ["/bin/bash", "-c"]
    command     = <<-EOT
      set -euo pipefail
      mkdir -p "$(dirname '${local.payload_path}')"
      "${var.edgectl_put_bin}" tls "${local.payload_path}"
    EOT
  }

  depends_on = [local_file.tls_payload]
}
