variable "cmdb" {
  type = map(object({
    workload           = string
    application        = string
    environment        = string
    owner              = string
    cost_center        = string
    patch_group        = string
    backup_tier        = string
    subnet_id          = string
    availability_zone  = string
    private_ip         = string
    instance_type      = string
    target_ami_id      = string
    security_group_ids = list(string)
    root_gib           = number
  }))
}

variable "disks" {
  type = map(list(object({
    device_name = string
    snapshot_id = string
    size_gib    = number
    volume_role = string
    iops        = number
    throughput  = number
  })))
}

variable "defaults" {
  type = object({
    region                      = string
    cutover_id                  = string
    migration_wave              = string
    kms_key_id                  = string
    iam_instance_profile        = string
    required_ssm_security_group = string
    forbidden_admin_groups      = list(string)
    disable_api_termination     = bool
    detailed_monitoring         = bool
    ebs_optimized               = bool
    metadata_http_tokens        = string
    metadata_hop_limit          = number
    metadata_instance_tags      = string
  })
}

variable "windows" {
  type = map(object({
    legacy_instance_id = string
    writer_role        = string
    dns_name           = string
  }))
}
