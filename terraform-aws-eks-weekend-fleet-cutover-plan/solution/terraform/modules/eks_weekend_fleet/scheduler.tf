resource "aws_scheduler_schedule_group" "weekend" {
  name = var.weekend_schedule.group_name

  tags = local.aws_tags
}

resource "aws_scheduler_schedule" "weekend" {
  for_each = local.weekend_schedules

  name       = each.value.name
  group_name = aws_scheduler_schedule_group.weekend.name
  state      = "ENABLED"

  schedule_expression          = each.value.schedule_expression
  schedule_expression_timezone = var.weekend_schedule.timezone

  flexible_time_window {
    mode                      = "FLEXIBLE"
    maximum_window_in_minutes = var.weekend_schedule.flexible_window_minutes
  }

  target {
    arn      = var.weekend_schedule.target_lambda_arn
    role_arn = var.weekend_schedule.scheduler_role_arn

    input = jsonencode({
      action       = each.key
      cluster_name = var.cluster_name
      region       = var.region
      node_groups  = each.value.sizes
    })
  }
}
