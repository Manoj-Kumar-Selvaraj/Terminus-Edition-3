output "blue_pool_id" {
  value = var.blue_pool.id
}

output "green_pool_id" {
  value = var.green_pool.id
}

output "blue_healthy_count" {
  value = local.blue_healthy_count
}

output "green_healthy_count" {
  value = local.green_healthy_count
}

output "blue_min_healthy" {
  value = var.blue_pool.min_healthy
}

output "green_min_healthy" {
  value = var.green_pool.min_healthy
}

output "blue_payload_path" {
  value = local.blue_payload_path
}

output "green_payload_path" {
  value = local.green_payload_path
}

output "applied_pool_ids" {
  value = [
    null_resource.put_blue_pool.triggers.pool_id,
    null_resource.put_green_pool.triggers.pool_id,
  ]
}
