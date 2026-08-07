# Frozen root outputs. Downstream pipelines read these five keys out of the
# rendered plan, so their names, types and ordering rules are fixed.

output "cluster_name" {
  description = "Name of the planned EKS cluster."
  value       = module.eks_weekend_fleet.cluster_name
}

output "node_group_names" {
  description = "Managed node group names, lexicographically sorted."
  value       = module.eks_weekend_fleet.node_group_names
}

output "irsa_role_arns" {
  description = "Map of workload identity name to the IAM role ARN it assumes."
  value       = module.eks_weekend_fleet.irsa_role_arns
}

output "weekend_schedule_names" {
  description = "EventBridge Scheduler schedule names, lexicographically sorted."
  value       = module.eks_weekend_fleet.weekend_schedule_names
}

output "monitoring_alarm_names" {
  description = "CloudWatch alarm names, lexicographically sorted."
  value       = module.eks_weekend_fleet.monitoring_alarm_names
}
