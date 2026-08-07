# Intentionally incomplete starter: keeps legacy admin groups, skips SSM
# injection, leaves IMDS optional, and does not encrypt restored volumes.

locals {
  workloads = var.cmdb
}

resource "aws_instance" "linux" {
  for_each = local.workloads

  ami                         = each.value.target_ami_id
  instance_type               = each.value.instance_type
  subnet_id                   = each.value.subnet_id
  private_ip                  = each.value.private_ip
  availability_zone           = each.value.availability_zone
  vpc_security_group_ids      = each.value.security_group_ids
  iam_instance_profile        = var.defaults.iam_instance_profile
  associate_public_ip_address = false
  disable_api_termination     = false
  monitoring                  = false
  ebs_optimized               = false

  root_block_device {
    volume_type = "gp3"
    volume_size = each.value.root_gib
    encrypted   = false
  }

  tags = {
    Name     = each.key
    Workload = each.key
  }
}

resource "aws_ebs_volume" "data" {
  for_each = {
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

  availability_zone = each.value.az
  size              = each.value.size_gib
  type              = "gp3"
  iops              = each.value.iops
  throughput        = each.value.throughput
  snapshot_id       = each.value.snapshot_id
  encrypted         = false

  tags = {
    Workload   = each.value.workload
    DeviceName = each.value.device_name
    VolumeRole = each.value.volume_role
  }
}

resource "aws_volume_attachment" "data" {
  for_each = aws_ebs_volume.data

  device_name = each.value.tags.DeviceName
  volume_id   = each.value.id
  instance_id = aws_instance.linux[each.value.tags.Workload].id
}
