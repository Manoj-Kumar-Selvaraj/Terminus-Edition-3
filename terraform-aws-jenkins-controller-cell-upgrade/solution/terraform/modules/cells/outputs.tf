output "cell_ids" {
  value = sort(keys(aws_ssm_parameter.cell))
}

output "home_claims" {
  value = sort([for k, ap in aws_efs_access_point.home : ap.tags["HomeClaim"]])
}
