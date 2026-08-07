resource "aws_cloudwatch_metric_alarm" "node_group_cpu" {
  for_each = var.node_groups

  alarm_name          = local.node_group_alarm_names[each.key]
  alarm_description   = "Sustained node CPU pressure on node group ${each.key}."
  namespace           = var.monitoring.metric_namespace
  metric_name         = var.monitoring.node_cpu_metric
  statistic           = "Average"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  threshold           = each.value.cpu_alarm_threshold_pct
  period              = var.monitoring.period_seconds
  evaluation_periods  = var.monitoring.evaluation_periods
  treat_missing_data  = "breaching"

  alarm_actions = [var.monitoring.alarm_topic_arn]
  ok_actions    = [var.monitoring.alarm_topic_arn]

  dimensions = {
    ClusterName   = var.cluster_name
    NodegroupName = each.key
  }

  tags = local.aws_tags
}

resource "aws_cloudwatch_metric_alarm" "cluster_cpu" {
  alarm_name          = local.cluster_alarm_name
  alarm_description   = "Fleet-wide node CPU pressure across ${var.cluster_name}."
  namespace           = var.monitoring.metric_namespace
  metric_name         = var.monitoring.node_cpu_metric
  statistic           = "Average"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  threshold           = var.monitoring.cluster_cpu_threshold_pct
  period              = var.monitoring.period_seconds
  evaluation_periods  = var.monitoring.evaluation_periods
  treat_missing_data  = "breaching"

  alarm_actions = [var.monitoring.alarm_topic_arn]
  ok_actions    = [var.monitoring.alarm_topic_arn]

  dimensions = {
    ClusterName = var.cluster_name
  }

  tags = local.aws_tags
}
