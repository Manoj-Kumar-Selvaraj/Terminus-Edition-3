output "ready_network_ids" {
  description = "Sorted network ids pushed to the live API as ready."
  value       = local.ready_ids
}

output "networks_by_region" {
  description = "Network ids grouped by region."
  value       = local.networks_by_region
}

output "networks_by_tier" {
  description = "Network ids grouped by fabric tier."
  value       = local.networks_by_tier
}

output "applied_markers" {
  description = "Per-network provisioner markers."
  value = {
    for id, r in null_resource.put_network : id => r.triggers.marker
  }
}

output "payload_paths" {
  description = "Rendered payload paths keyed by network id."
  value       = local.payload_filenames
}

output "region_catalog_keys" {
  description = "Known region catalog keys (superset of inventory)."
  value       = sort(keys(local.region_catalog))
}
