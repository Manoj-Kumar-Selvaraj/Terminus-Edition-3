# WIP edge module — intentionally unsafe / incomplete. Fix per
# /app/docs/edge-exception-contract.md and the evidence under /app/evidence.

locals {
  origins_by_id = { for o in var.origins : o.origin_id => o }
}

resource "aws_s3_bucket" "static" {
  bucket = local.origins_by_id["s3-static"].bucket_name
}

resource "aws_s3_bucket" "failover" {
  provider = aws.failover
  bucket   = local.origins_by_id["failover-static"].bucket_name
}

# Legacy OAI path — contract requires an origin access control (OAC) relation.
resource "aws_cloudfront_origin_access_identity" "static" {
  comment = "legacy oai"
}

resource "aws_cloudfront_cache_policy" "no_cache" {
  name        = "edge-no-cache"
  default_ttl = 0
  max_ttl     = 0
  min_ttl     = 0
  parameters_in_cache_key_and_forwarded_to_origin {
    cookies_config {
      cookie_behavior = "none"
    }
    headers_config {
      header_behavior = "none"
    }
    query_strings_config {
      query_string_behavior = "none"
    }
  }
}

resource "aws_wafv2_web_acl" "platform" {
  name  = "platform-edge-waf-draft"
  scope = "CLOUDFRONT"
  default_action {
    allow {}
  }
  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "platform-edge-waf-draft"
    sampled_requests_enabled   = true
  }
}

resource "aws_cloudfront_distribution" "edge" {
  enabled     = true
  comment     = "static-api"
  price_class = "PriceClass_100"
  web_acl_id  = aws_wafv2_web_acl.platform.arn

  origin {
    domain_name = aws_s3_bucket.static.bucket_regional_domain_name
    origin_id   = "s3-static"
    s3_origin_config {
      origin_access_identity = aws_cloudfront_origin_access_identity.static.cloudfront_access_identity_path
    }
  }

  origin {
    domain_name = local.origins_by_id["api"].domain_name
    origin_id   = "api"
    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
    custom_header {
      name  = local.origins_by_id["api"].custom_header_name
      value = local.origins_by_id["api"].custom_header_value
    }
  }

  default_cache_behavior {
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "s3-static"
    viewer_protocol_policy = "allow-all"
    cache_policy_id        = "658327ea-f89d-4fab-a63d-7e88639e58f6"
  }

  ordered_cache_behavior {
    path_pattern           = "/api/*"
    allowed_methods        = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "api"
    viewer_protocol_policy = "redirect-to-https"
    cache_policy_id        = aws_cloudfront_cache_policy.no_cache.id
  }

  logging_config {
    include_cookies = false
    bucket          = "claims-edge-logs"
    prefix          = "static-api/"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
    minimum_protocol_version       = "TLSv1"
  }
}

resource "aws_cloudfront_distribution" "failover" {
  enabled     = true
  comment     = "failover"
  price_class = "PriceClass_100"
  web_acl_id  = aws_wafv2_web_acl.platform.arn

  origin {
    domain_name = aws_s3_bucket.failover.bucket_regional_domain_name
    origin_id   = "failover-static"
    s3_origin_config {
      origin_access_identity = aws_cloudfront_origin_access_identity.static.cloudfront_access_identity_path
    }
  }

  default_cache_behavior {
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "failover-static"
    viewer_protocol_policy = "redirect-to-https"
    cache_policy_id        = "658327ea-f89d-4fab-a63d-7e88639e58f6"
  }

  logging_config {
    include_cookies = false
    bucket          = "claims-edge-logs"
    prefix          = "failover/"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
    minimum_protocol_version       = "TLSv1.2_2021"
  }
}

resource "aws_cloudfront_distribution" "signed_content" {
  enabled     = true
  comment     = "signed-content"
  price_class = "PriceClass_100"
  web_acl_id  = aws_wafv2_web_acl.platform.arn

  origin {
    domain_name = aws_s3_bucket.static.bucket_regional_domain_name
    origin_id   = "s3-static"
    s3_origin_config {
      origin_access_identity = aws_cloudfront_origin_access_identity.static.cloudfront_access_identity_path
    }
  }

  default_cache_behavior {
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "s3-static"
    viewer_protocol_policy = "redirect-to-https"
    trusted_signers        = ["self"]
    cache_policy_id        = "658327ea-f89d-4fab-a63d-7e88639e58f6"
  }

  logging_config {
    include_cookies = false
    bucket          = "claims-edge-logs"
    prefix          = "signed/"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
    minimum_protocol_version       = "TLSv1.2_2021"
  }
}

resource "aws_s3_bucket_policy" "static" {
  bucket = aws_s3_bucket.static.id
  policy = <<POLICY
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "${aws_s3_bucket.static.arn}/*"
    }
  ]
}
POLICY
}

resource "aws_s3_bucket_policy" "failover" {
  provider = aws.failover
  bucket   = aws_s3_bucket.failover.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = "*"
      Action    = "s3:GetObject"
      Resource  = ["${aws_s3_bucket.failover.arn}/*"]
    }]
  })
}
