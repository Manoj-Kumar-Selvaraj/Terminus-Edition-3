resource "local_file" "probe_spec" {
  for_each = local.probes_by_id

  filename = local.probe_files[each.key]
  content = jsonencode({
    id                = each.value.id
    name              = each.value.name
    path              = each.value.path
    method            = each.value.method
    expect_status     = each.value.expect_status
    timeout_ms        = each.value.timeout_ms
    headers           = each.value.headers
    region_preference = each.value.region_preference
    hostname          = var.hostname
    dns_fqdn          = var.dns_fqdn
    green_pool        = var.green_pool
    engagement        = var.engagement
    catalog           = lookup(local.probe_catalog, each.key, {})
  })
  file_permission = "0644"
}

resource "local_file" "probe_index" {
  filename        = "${var.output_dir}/index.json"
  content         = jsonencode(local.index_document)
  file_permission = "0644"

  depends_on = [local_file.probe_spec]
}

resource "null_resource" "observatory_ready_marker" {
  triggers = {
    engagement  = var.engagement
    probe_count = tostring(length(var.probes))
    index_sha   = local_file.probe_index.content_sha256
    green_pool  = var.green_pool
    dns_fqdn    = var.dns_fqdn
  }

  provisioner "local-exec" {
    interpreter = ["/bin/bash", "-c"]
    command     = <<-EOT
      set -euo pipefail
      test -s "${var.output_dir}/index.json"
      test "$(find "${var.output_dir}" -name 'probe-*.json' | wc -l)" -ge 1
    EOT
  }

  depends_on = [
    local_file.probe_spec,
    local_file.probe_index,
  ]
}
