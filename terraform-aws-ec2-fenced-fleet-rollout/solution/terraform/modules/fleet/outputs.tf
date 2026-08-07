output "launch_template_name_prefix" {
  value = aws_launch_template.this.name_prefix
}

output "autoscaling_group_name" {
  value = aws_autoscaling_group.this.name
}

output "security_group_id" {
  value = aws_security_group.instance.id
}

output "iam_role_name" {
  value = aws_iam_role.instance.name
}

output "volume_slots" {
  value = sort([for v in aws_ebs_volume.data : v.tags.Slot])
}

output "launch_template_image_id" {
  value = aws_launch_template.this.image_id
}

output "metadata_http_tokens" {
  value = aws_launch_template.this.metadata_options[0].http_tokens
}
