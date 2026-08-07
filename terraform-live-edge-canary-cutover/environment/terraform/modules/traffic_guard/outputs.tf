output "ok" {
  description = "True when the guard ran (or was intentionally disabled)."
  value       = var.enabled ? length(null_resource.metrics_assert) == 1 : false
}

output "enabled" {
  value = var.enabled
}

output "max_error_rate_pct" {
  value = var.max_error_rate_pct
}

output "expect_pool" {
  value = var.expect_pool
}

output "guard_policy" {
  value = local.guard_policy
}

output "failure_modes" {
  value = local.failure_modes
}

output "remediation" {
  value = local.remediation
}
