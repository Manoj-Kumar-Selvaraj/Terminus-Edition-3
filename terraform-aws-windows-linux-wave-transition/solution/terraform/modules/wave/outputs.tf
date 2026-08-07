output "instance_workloads" {
  value = sort(keys(aws_instance.linux))
}

output "volume_keys" {
  value = sort(keys(aws_ebs_volume.data))
}
