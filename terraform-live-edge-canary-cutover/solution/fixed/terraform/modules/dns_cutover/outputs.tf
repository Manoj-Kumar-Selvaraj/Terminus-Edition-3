output "target_pool" {
  value = var.target_pool
}

output "fqdn" {
  value = local.fqdn
}

output "payload_path" {
  value = local.payload_path
}

output "require_canary_weight" {
  value = var.require_canary_weight
}

output "cutover_notes" {
  value = local.cutover_notes
}

output "rollback" {
  value = local.rollback
}
