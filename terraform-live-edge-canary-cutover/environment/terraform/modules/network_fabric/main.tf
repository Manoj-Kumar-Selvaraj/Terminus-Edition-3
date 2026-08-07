resource "local_file" "network_payload" {
  for_each = local.normalized

  filename        = local.payload_filenames[each.key]
  content         = jsonencode(each.value.api_body)
  file_permission = "0644"
}

resource "null_resource" "put_network" {
  for_each = local.normalized

  triggers = {
    marker      = each.value.marker
    payload     = local_file.network_payload[each.key].content_sha256
    engagement  = var.engagement
    base_url    = var.base_url
    network_id  = each.value.id
    status      = "ready"
  }

  provisioner "local-exec" {
    interpreter = ["/bin/bash", "-c"]
    command     = <<-EOT
      set -euo pipefail
      mkdir -p "$(dirname '${local.payload_filenames[each.key]}')"
      "${var.edgectl_put_bin}" network "${local.payload_filenames[each.key]}"
    EOT
  }

  depends_on = [local_file.network_payload]
}
