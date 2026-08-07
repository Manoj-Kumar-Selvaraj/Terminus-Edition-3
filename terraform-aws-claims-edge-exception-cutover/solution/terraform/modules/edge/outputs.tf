output "distribution_ids" {
  value = {
    "static-api"     = aws_cloudfront_distribution.edge.id
    "failover"       = aws_cloudfront_distribution.failover.id
    "signed-content" = aws_cloudfront_distribution.signed_content.id
  }
}

output "origin_access_control_ids" {
  value = {
    "s3-static"       = aws_cloudfront_origin_access_control.static.id
    "failover-static" = aws_cloudfront_origin_access_control.failover.id
  }
}

output "web_acl_arns" {
  value = {
    platform = aws_wafv2_web_acl.platform.arn
  }
}

output "bucket_names" {
  value = {
    static   = aws_s3_bucket.static.bucket
    failover = aws_s3_bucket.failover.bucket
  }
}

output "signed_path_patterns" {
  value = distinct([for e in local.approved_exceptions : e.path_pattern])
}
