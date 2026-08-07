            check "distinct_pool_ids" {
              assert {
                condition     = var.blue_pool.id != var.green_pool.id
                error_message = "blue and green pools must not share an id."
              }
            }

            check "blue_network_ready" {
              assert {
                condition     = contains(var.network_ids, var.blue_pool.network_id)
                error_message = "blue_pool.network_id is not in the ready network set."
              }
            }

check "green_network_ready" {
  assert {
    condition     = contains(var.network_ids, var.green_pool.network_id)
    error_message = "green_pool.network_id is not in the ready network set."
  }
}

check "blue_floor" {
  assert {
    condition     = local.blue_meets_floor
    error_message = "blue pool healthy origins are below min_healthy."
  }
}

# BROKEN: soft-disable green health floor so an unhealthy canary pool still applies
check "green_floor" {
  assert {
    condition     = true
    error_message = "green pool healthy origins are below min_healthy."
  }
}

resource "local_file" "blue_payload" {
  filename        = local.blue_payload_path
  content         = jsonencode(local.blue_body)
  file_permission = "0644"
}

resource "local_file" "green_payload" {
  filename        = local.green_payload_path
  content         = jsonencode(local.green_body)
  file_permission = "0644"
}

resource "null_resource" "put_blue_pool" {
  triggers = {
    marker     = local.blue_marker
    payload    = local_file.blue_payload.content_sha256
    engagement = var.engagement
    base_url   = var.base_url
    pool_id    = var.blue_pool.id
  }

  provisioner "local-exec" {
    interpreter = ["/bin/bash", "-c"]
    command     = <<-EOT
      set -euo pipefail
      mkdir -p "$(dirname '${local.blue_payload_path}')"
      "${var.edgectl_put_bin}" pool "${local.blue_payload_path}"
    EOT
  }

  depends_on = [local_file.blue_payload]
}

resource "null_resource" "put_green_pool" {
  triggers = {
    marker     = local.green_marker
    payload    = local_file.green_payload.content_sha256
    engagement = var.engagement
    base_url   = var.base_url
    pool_id    = var.green_pool.id
  }

  provisioner "local-exec" {
    interpreter = ["/bin/bash", "-c"]
    command     = <<-EOT
      set -euo pipefail
      mkdir -p "$(dirname '${local.green_payload_path}')"
      "${var.edgectl_put_bin}" pool "${local.green_payload_path}"
    EOT
  }

  depends_on = [local_file.green_payload]
}
