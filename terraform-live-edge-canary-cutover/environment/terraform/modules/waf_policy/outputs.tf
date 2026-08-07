output "waf_id" {
  value = var.waf.id
}

output "applied_mode" {
  value = var.final_mode
}

output "rule_ids" {
  value = local.rule_ids
}

output "rule_count" {
  value = length(local.api_rules)
}

output "severity_counts" {
  value = local.severity_counts
}

output "payload_path" {
  value = local.payload_path
}
