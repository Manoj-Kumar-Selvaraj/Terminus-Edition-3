output "steps_applied" {
  description = "Ordered canary weights from inventory."
  value       = var.canary_steps
}

output "final_weight" {
  value = local.final_weight
}

output "route_id" {
  value = var.route_id
}

output "final_step_resource_id" {
  description = "Stable id consumed by dns_cutover depends_on wiring."
  value       = "${var.route_id}:final:${local.final_weight}"
}

output "step_keys_ordered" {
  value = local.step_keys_ordered
}

output "bake_guidance" {
  value = local.bake_guidance
}

output "step_runbook" {
  value = local.step_runbook
}
