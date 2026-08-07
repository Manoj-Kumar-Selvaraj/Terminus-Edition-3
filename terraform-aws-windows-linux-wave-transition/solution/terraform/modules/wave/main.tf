locals {
  forbidden = toset(var.defaults.forbidden_admin_groups)

  sanitized_sgs = {
    for wl, rec in var.cmdb :
    wl => distinct(concat(
      [for sg in rec.security_group_ids : sg if !contains(local.forbidden, sg)],
      [var.defaults.required_ssm_security_group]
    ))
  }

  volume_map = {
    for pair in flatten([
      for wl, vols in var.disks : [
        for v in vols : {
          key         = "${wl}:${v.device_name}"
          workload    = wl
          device_name = v.device_name
          snapshot_id = v.snapshot_id
          size_gib    = v.size_gib
          volume_role = v.volume_role
          iops        = v.iops
          throughput  = v.throughput
          az          = var.cmdb[wl].availability_zone
        }
      ]
    ]) : pair.key => pair
  }
}

resource "aws_instance" "linux" {
  for_each = var.cmdb

  ami                         = each.value.target_ami_id
  instance_type               = each.value.instance_type
  subnet_id                   = each.value.subnet_id
  private_ip                  = each.value.private_ip
  availability_zone           = each.value.availability_zone
  vpc_security_group_ids      = local.sanitized_sgs[each.key]
  iam_instance_profile        = var.defaults.iam_instance_profile
  associate_public_ip_address = false
  disable_api_termination     = var.defaults.disable_api_termination
  monitoring                  = var.defaults.detailed_monitoring
  ebs_optimized               = var.defaults.ebs_optimized

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = var.defaults.metadata_http_tokens
    http_put_response_hop_limit = var.defaults.metadata_hop_limit
    instance_metadata_tags      = var.defaults.metadata_instance_tags
  }

  root_block_device {
    volume_type = "gp3"
    volume_size = each.value.root_gib
    encrypted   = true
    kms_key_id  = var.defaults.kms_key_id

    tags = {
      VolumeRole = "root"
      Workload   = each.key
    }
  }

  tags = {
    Name             = each.key
    Workload         = each.key
    Application      = each.value.application
    Environment      = each.value.environment
    Owner            = each.value.owner
    OwnerCostCenter  = each.value.cost_center
    PatchGroup       = each.value.patch_group
    BackupTier      = each.value.backup_tier
    MigratedFromOS   = "windows"
    OSFamily         = "linux"
    LegacyInstanceId = var.windows[each.key].legacy_instance_id
    CutoverId        = var.defaults.cutover_id
    MigrationWave    = var.defaults.migration_wave
    ManagedBy        = "terraform"
  }
}

resource "aws_ebs_volume" "data" {
  for_each = local.volume_map

  availability_zone = each.value.az
  size              = each.value.size_gib
  type              = "gp3"
  iops              = each.value.iops
  throughput        = each.value.throughput
  snapshot_id       = each.value.snapshot_id
  encrypted         = true
  kms_key_id        = var.defaults.kms_key_id

  tags = {
    Workload       = each.value.workload
    DeviceName     = each.value.device_name
    VolumeRole     = each.value.volume_role
    SourceSnapshot = each.value.snapshot_id
  }
}

resource "aws_volume_attachment" "data" {
  for_each = aws_ebs_volume.data

  device_name  = each.value.tags["DeviceName"]
  volume_id    = each.value.id
  instance_id  = aws_instance.linux[each.value.tags["Workload"]].id
  force_detach = false
}
