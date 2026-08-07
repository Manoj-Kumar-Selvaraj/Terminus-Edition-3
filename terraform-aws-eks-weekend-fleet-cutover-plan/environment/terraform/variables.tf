# Root inputs. Every value is supplied by weekend-fleet.auto.tfvars.json.
# This file is part of the frozen root configuration.

variable "region" {
  type        = string
  description = "AWS region hosting the weekend fleet."
}

variable "account_id" {
  type        = string
  description = "Account that owns the fleet; used to compose ARNs without a caller-identity lookup."
}

variable "resource_prefix" {
  type        = string
  description = "Short prefix applied to every named resource."
}

variable "cluster_name" {
  type        = string
  description = "EKS cluster name."
}

variable "kubernetes_version" {
  type        = string
  description = "Control plane Kubernetes minor version."
}

variable "vpc_id" {
  type        = string
  description = "VPC that hosts the cluster."
}

variable "private_subnet_ids" {
  type        = list(string)
  description = "Private subnets for the control plane ENIs and every node group."
}

variable "cluster_security_group_id" {
  type        = string
  description = "Pre-provisioned control plane security group."
}

variable "oidc_provider_arn" {
  type        = string
  description = "Pre-provisioned IAM OIDC provider for the cluster."
}

variable "oidc_provider_url" {
  type        = string
  description = "Host and path of the cluster OIDC issuer, without the scheme."
}

variable "cluster_log_types" {
  type        = list(string)
  description = "Control plane log types that must reach CloudWatch."
}

variable "cluster_log_retention_days" {
  type        = number
  description = "Retention for the control plane log group."
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
  description = "Managed node group fleet, keyed by node group name."
}

variable "cluster_addons" {
  type = map(object({
    addon_version               = string
    resolve_conflicts_on_update = string
    irsa_role                   = string
  }))
  description = "Core EKS add-ons, keyed by add-on name."
}

variable "irsa_roles" {
  type = map(object({
    namespace       = string
    service_account = string
  }))
  description = "IRSA roles to create, keyed by workload identity name."
}

variable "helm_releases" {
  type = map(object({
    chart_dir     = string
    chart_version = string
    namespace     = string
    irsa_role     = string
    set_values    = map(string)
  }))
  description = "Helm releases rendered from vendored charts, keyed by release name."
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
  description = "Artifactory credential helper wiring."
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
  description = "CloudWatch alarm parameters."
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
  description = "EventBridge Scheduler parameters for the weekend cutover."
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
  description = "ALB ingress class and placeholder ingress parameters."
}

variable "tags" {
  type        = map(string)
  description = "Baseline tags applied to every taggable AWS resource."
}
