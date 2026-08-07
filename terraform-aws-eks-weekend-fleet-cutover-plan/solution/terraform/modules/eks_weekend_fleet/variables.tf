variable "region" {
  type = string
}

variable "account_id" {
  type = string
}

variable "resource_prefix" {
  type = string
}

variable "cluster_name" {
  type = string
}

variable "kubernetes_version" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "private_subnet_ids" {
  type = list(string)
}

variable "cluster_security_group_id" {
  type = string
}

variable "oidc_provider_arn" {
  type = string
}

variable "oidc_provider_url" {
  type = string
}

variable "cluster_log_types" {
  type = list(string)
}

variable "cluster_log_retention_days" {
  type = number
}

variable "node_groups" {
  type = map(object({
    capacity_type           = string
    ami_type                = string
    release_version         = string
    instance_types          = list(string)
    disk_size_gb            = number
    min_size                = number
    desired_size            = number
    max_size                = number
    max_unavailable         = number
    weekend_parked          = bool
    labels                  = map(string)
    cpu_alarm_threshold_pct = number
  }))
}

variable "cluster_addons" {
  type = map(object({
    addon_version               = string
    resolve_conflicts_on_update = string
    irsa_role                   = string
  }))
}

variable "irsa_roles" {
  type = map(object({
    namespace       = string
    service_account = string
  }))
}

variable "helm_releases" {
  type = map(object({
    chart_dir     = string
    chart_version = string
    namespace     = string
    irsa_role     = string
    set_values    = map(string)
  }))
}

variable "artifactory" {
  type = object({
    registry_host            = string
    namespace                = string
    daemonset_name           = string
    pull_secret_name         = string
    helper_image             = string
    username_secret_key      = string
    password_secret_key      = string
    refresh_interval_seconds = number
  })
}

variable "monitoring" {
  type = object({
    metric_namespace          = string
    node_cpu_metric           = string
    period_seconds            = number
    evaluation_periods        = number
    cluster_cpu_threshold_pct = number
    alarm_topic_arn           = string
  })
}

variable "weekend_schedule" {
  type = object({
    group_name              = string
    timezone                = string
    scale_down_cron         = string
    scale_up_cron           = string
    flexible_window_minutes = number
    target_lambda_arn       = string
    scheduler_role_arn      = string
  })
}

variable "ingress" {
  type = object({
    ingress_class_name = string
    controller         = string
    namespace          = string
    placeholder_name   = string
    placeholder_host   = string
    scheme             = string
    target_type        = string
    service_name       = string
    service_port       = number
  })
}

variable "tags" {
  type = map(string)
}

variable "chart_root" {
  type = string
}
