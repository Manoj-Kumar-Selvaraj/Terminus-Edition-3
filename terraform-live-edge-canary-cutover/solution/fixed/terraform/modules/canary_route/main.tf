check "canary_monotonic" {
  assert {
    condition     = !var.require_monotonic || local.monotonic_ok
    error_message = "canary_steps must be strictly increasing when require_monotonic is true."
  }
}

check "pools_echo" {
  assert {
    condition = (
      var.blue_pool_applied_id == var.blue_pool_id &&
      var.green_pool_applied_id == var.green_pool_id
    )
    error_message = "canary_route pool ids must match origin_pool outputs."
  }
}

resource "local_file" "canary_payload" {
  for_each = local.steps

  filename        = each.value.payload_path
  content         = jsonencode(each.value.body)
  file_permission = "0644"
}

# Ordered canary step resources. Explicit depends_on chain ensures
# Terraform cannot reorder weight increases relative to inventory.

resource "null_resource" "canary_step_00" {
  count = local.step_count >= 1 ? 1 : 0

  triggers = {
    marker     = local.steps[local.step_keys_ordered[0]].marker
    payload    = local_file.canary_payload[local.step_keys_ordered[0]].content_sha256
    engagement = var.engagement
    base_url   = var.base_url
    route_id   = var.route_id
    weight     = tostring(local.steps[local.step_keys_ordered[0]].weight)
    index      = "0"
  }

  provisioner "local-exec" {
    interpreter = ["/bin/bash", "-c"]
    command     = <<-EOT
      set -euo pipefail
      "${var.edgectl_put_bin}" canary "${local.steps[local.step_keys_ordered[0]].payload_path}"
    EOT
  }

  depends_on = [local_file.canary_payload]
}

resource "null_resource" "canary_step_01" {
  count = local.step_count >= 2 ? 1 : 0

  triggers = {
    marker     = local.steps[local.step_keys_ordered[1]].marker
    payload    = local_file.canary_payload[local.step_keys_ordered[1]].content_sha256
    engagement = var.engagement
    base_url   = var.base_url
    route_id   = var.route_id
    weight     = tostring(local.steps[local.step_keys_ordered[1]].weight)
    index      = "1"
  }

  provisioner "local-exec" {
    interpreter = ["/bin/bash", "-c"]
    command     = <<-EOT
      set -euo pipefail
      "${var.edgectl_put_bin}" canary "${local.steps[local.step_keys_ordered[1]].payload_path}"
    EOT
  }

  depends_on = [
    local_file.canary_payload,
    null_resource.canary_step_00,
  ]
}

resource "null_resource" "canary_step_02" {
  count = local.step_count >= 3 ? 1 : 0

  triggers = {
    marker     = local.steps[local.step_keys_ordered[2]].marker
    payload    = local_file.canary_payload[local.step_keys_ordered[2]].content_sha256
    engagement = var.engagement
    base_url   = var.base_url
    route_id   = var.route_id
    weight     = tostring(local.steps[local.step_keys_ordered[2]].weight)
    index      = "2"
  }

  provisioner "local-exec" {
    interpreter = ["/bin/bash", "-c"]
    command     = <<-EOT
      set -euo pipefail
      "${var.edgectl_put_bin}" canary "${local.steps[local.step_keys_ordered[2]].payload_path}"
    EOT
  }

  depends_on = [
    local_file.canary_payload,
    null_resource.canary_step_01,
  ]
}

resource "null_resource" "canary_step_03" {
  count = local.step_count >= 4 ? 1 : 0

  triggers = {
    marker     = local.steps[local.step_keys_ordered[3]].marker
    payload    = local_file.canary_payload[local.step_keys_ordered[3]].content_sha256
    engagement = var.engagement
    base_url   = var.base_url
    route_id   = var.route_id
    weight     = tostring(local.steps[local.step_keys_ordered[3]].weight)
    index      = "3"
  }

  provisioner "local-exec" {
    interpreter = ["/bin/bash", "-c"]
    command     = <<-EOT
      set -euo pipefail
      "${var.edgectl_put_bin}" canary "${local.steps[local.step_keys_ordered[3]].payload_path}"
    EOT
  }

  depends_on = [
    local_file.canary_payload,
    null_resource.canary_step_02,
  ]
}

resource "null_resource" "canary_step_04" {
  count = local.step_count >= 5 ? 1 : 0

  triggers = {
    marker     = local.steps[local.step_keys_ordered[4]].marker
    payload    = local_file.canary_payload[local.step_keys_ordered[4]].content_sha256
    engagement = var.engagement
    base_url   = var.base_url
    route_id   = var.route_id
    weight     = tostring(local.steps[local.step_keys_ordered[4]].weight)
    index      = "4"
  }

  provisioner "local-exec" {
    interpreter = ["/bin/bash", "-c"]
    command     = <<-EOT
      set -euo pipefail
      "${var.edgectl_put_bin}" canary "${local.steps[local.step_keys_ordered[4]].payload_path}"
    EOT
  }

  depends_on = [
    local_file.canary_payload,
    null_resource.canary_step_03,
  ]
}

resource "null_resource" "canary_step_05" {
  count = local.step_count >= 6 ? 1 : 0

  triggers = {
    marker     = local.steps[local.step_keys_ordered[5]].marker
    payload    = local_file.canary_payload[local.step_keys_ordered[5]].content_sha256
    engagement = var.engagement
    base_url   = var.base_url
    route_id   = var.route_id
    weight     = tostring(local.steps[local.step_keys_ordered[5]].weight)
    index      = "5"
  }

  provisioner "local-exec" {
    interpreter = ["/bin/bash", "-c"]
    command     = <<-EOT
      set -euo pipefail
      "${var.edgectl_put_bin}" canary "${local.steps[local.step_keys_ordered[5]].payload_path}"
    EOT
  }

  depends_on = [
    local_file.canary_payload,
    null_resource.canary_step_04,
  ]
}

resource "null_resource" "canary_step_06" {
  count = local.step_count >= 7 ? 1 : 0

  triggers = {
    marker     = local.steps[local.step_keys_ordered[6]].marker
    payload    = local_file.canary_payload[local.step_keys_ordered[6]].content_sha256
    engagement = var.engagement
    base_url   = var.base_url
    route_id   = var.route_id
    weight     = tostring(local.steps[local.step_keys_ordered[6]].weight)
    index      = "6"
  }

  provisioner "local-exec" {
    interpreter = ["/bin/bash", "-c"]
    command     = <<-EOT
      set -euo pipefail
      "${var.edgectl_put_bin}" canary "${local.steps[local.step_keys_ordered[6]].payload_path}"
    EOT
  }

  depends_on = [
    local_file.canary_payload,
    null_resource.canary_step_05,
  ]
}

resource "null_resource" "canary_step_07" {
  count = local.step_count >= 8 ? 1 : 0

  triggers = {
    marker     = local.steps[local.step_keys_ordered[7]].marker
    payload    = local_file.canary_payload[local.step_keys_ordered[7]].content_sha256
    engagement = var.engagement
    base_url   = var.base_url
    route_id   = var.route_id
    weight     = tostring(local.steps[local.step_keys_ordered[7]].weight)
    index      = "7"
  }

  provisioner "local-exec" {
    interpreter = ["/bin/bash", "-c"]
    command     = <<-EOT
      set -euo pipefail
      "${var.edgectl_put_bin}" canary "${local.steps[local.step_keys_ordered[7]].payload_path}"
    EOT
  }

  depends_on = [
    local_file.canary_payload,
    null_resource.canary_step_06,
  ]
}
