output "engagement" {
  description = "Engagement identifier from inventory."
  value       = local.engagement
}

output "edge_hostname" {
  description = "Canonical edge hostname under cutover."
  value       = local.edge_hostname
}

output "phase_order" {
  description = "Documented module phase order for operators."
  value       = local.phase_order
}

output "cutover_context" {
  description = "Compact cutover context assembled from inventory."
  value       = local.cutover_context
}

output "ready_network_ids" {
  description = "Network ids declared ready by network_fabric."
  value       = module.network_fabric.ready_network_ids
}

output "blue_pool_id" {
  description = "Blue origin pool id applied to the live API."
  value       = module.origin_pool.blue_pool_id
}

output "green_pool_id" {
  description = "Green origin pool id applied to the live API."
  value       = module.origin_pool.green_pool_id
}

output "waf_id" {
  description = "WAF policy id installed on the live API."
  value       = module.waf_policy.waf_id
}

output "waf_mode" {
  description = "Final WAF mode after apply."
  value       = module.waf_policy.applied_mode
}

output "tls_id" {
  description = "TLS material id installed for the edge hostname."
  value       = module.tls_material.tls_id
}

output "tls_fingerprint" {
  description = "TLS fingerprint asserted against inventory."
  value       = module.tls_material.applied_fingerprint
}

output "canary_steps_applied" {
  description = "Ordered canary weights applied to the live route."
  value       = module.canary_route.steps_applied
}

output "dns_target_pool" {
  description = "Pool selected by DNS cutover."
  value       = module.dns_cutover.target_pool
}

output "observatory_probe_count" {
  description = "Number of observatory probe specs written."
  value       = module.observatory.probe_count
}

output "traffic_guard_ok" {
  description = "Whether traffic_guard accepted live metrics."
  value       = module.traffic_guard.ok
}

output "error_budget_pct" {
  description = "Inventory error budget used by traffic_guard."
  value       = local.error_budget_pct
}
