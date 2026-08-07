output "cluster_name" {
  value = aws_eks_cluster.this.name
}

output "node_group_names" {
  value = sort(keys(var.node_groups))
}

output "irsa_role_arns" {
  value = local.irsa_role_arns
}

output "weekend_schedule_names" {
  value = sort([for schedule in values(local.weekend_schedules) : schedule.name])
}

output "monitoring_alarm_names" {
  value = sort(concat(values(local.node_group_alarm_names), [local.cluster_alarm_name]))
}
