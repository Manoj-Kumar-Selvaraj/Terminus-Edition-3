provider "aws" {
  region                      = var.region
  access_key                  = "test"
  secret_key                  = "test"
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true
  skip_region_validation      = true
}

variable "region" {
  type    = string
  default = "us-east-1"
}

variable "config_path" {
  type    = string
  default = "/app/data/fleet_config.json"
}

locals {
  cfg      = jsondecode(file(var.config_path))
  artifact = local.cfg.release_artifact
  asg      = local.cfg.asg
  network  = local.cfg.network
  volumes  = local.cfg.ebs_volumes
  subnets  = [for s in local.cfg.placement.subnets : s.id]
}

module "fleet" {
  source = "../../modules/fleet"

  account_id                 = local.cfg.account_id
  region                    = local.cfg.region
  app                       = local.cfg.app
  environment               = local.cfg.environment
  instance_type             = local.cfg.instance_type
  service_port              = local.cfg.service_port
  artifact_bucket_arn       = local.cfg.artifact_bucket_arn
  metric_namespace          = local.cfg.metric_namespace
  ami_id                    = local.artifact.ami_id
  ami_architecture          = local.artifact.architecture
  user_data_sha256          = local.artifact.user_data_sha256
  commit_sha                = local.artifact.commit_sha
  build_id                  = local.artifact.build_id
  manifest_sha256           = local.artifact.manifest_sha256
  desired_capacity          = local.asg.desired_capacity
  min_size                  = local.asg.min_size
  max_size                  = local.asg.max_size
  max_unavailable           = local.asg.max_unavailable
  subnet_ids                = local.subnets
  alb_security_group_id     = local.network.alb_security_group_id
  resolver_security_group_id = local.network.resolver_security_group_id
  endpoint_prefix_lists     = local.network.endpoint_prefix_lists
  ebs_volumes               = local.volumes
  slot_count                = local.asg.desired_capacity
}
