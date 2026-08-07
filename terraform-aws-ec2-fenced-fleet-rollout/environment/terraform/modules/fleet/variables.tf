variable "account_id" { type = string }
variable "region" { type = string }
variable "app" { type = string }
variable "environment" { type = string }
variable "instance_type" { type = string }
variable "service_port" { type = number }
variable "artifact_bucket_arn" { type = string }
variable "metric_namespace" { type = string }
variable "ami_id" { type = string }
variable "ami_architecture" { type = string }
variable "user_data_sha256" { type = string }
variable "commit_sha" { type = string }
variable "build_id" { type = string }
variable "manifest_sha256" { type = string }
variable "desired_capacity" { type = number }
variable "min_size" { type = number }
variable "max_size" { type = number }
variable "max_unavailable" { type = number }
variable "subnet_ids" { type = list(string) }
variable "alb_security_group_id" { type = string }
variable "resolver_security_group_id" { type = string }
variable "endpoint_prefix_lists" { type = list(string) }
variable "ebs_volumes" {
  type = list(object({
    logical_name           = string
    size_gb                = number
    encrypted              = bool
    kms_key_alias          = string
    kms_key_arn            = string
    delete_on_termination  = bool
  }))
}
variable "slot_count" { type = number }
