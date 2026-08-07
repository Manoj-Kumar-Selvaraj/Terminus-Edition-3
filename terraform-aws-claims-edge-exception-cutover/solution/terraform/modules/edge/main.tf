locals {
  distribution_names = ["static-api", "failover", "signed-content"]

  origins_by_id = { for o in var.origins : o.origin_id => o }

  rules_by_dist = {
    for dist in local.distribution_names :
    dist => [for r in var.path_rules : r if r.distribution == dist]
  }

  default_rule_by_dist = {
    for dist in local.distribution_names :
    dist => one([for r in local.rules_by_dist[dist] : r if r.path == "/*"])
  }

  ordered_rules_by_dist = {
    for dist in local.distribution_names :
    dist => {
      for r in local.rules_by_dist[dist] :
      format("%05d-%s", r.priority, r.path) => r
      if r.path != "/*"
    }
  }

  origin_ids_by_dist = {
    for dist in local.distribution_names :
    dist => distinct([for r in local.rules_by_dist[dist] : r.origin_id])
  }

  fallback_origin_by_dist = {
    for dist in local.distribution_names :
    dist => try(local.default_rule_by_dist[dist].origin_id, values(local.ordered_rules_by_dist[dist])[0].origin_id)
  }

  logging_by_dist = { for l in var.logging_policy : l.distribution => l }

  approved_exceptions = [for e in var.exception_requests : e if e.status == "approved"]
}

resource "aws_s3_bucket" "static" {
  bucket = local.origins_by_id["s3-static"].bucket_name
}

resource "aws_s3_bucket" "failover" {
  provider = aws.failover
  bucket   = local.origins_by_id["failover-static"].bucket_name
}

resource "aws_s3_bucket_public_access_block" "static" {
  bucket                  = aws_s3_bucket.static.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_public_access_block" "failover" {
  provider                = aws.failover
  bucket                  = aws_s3_bucket.failover.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_cloudfront_origin_access_control" "static" {
  name                              = "claims-static-oac"
  description                       = "OAC for ${local.origins_by_id["s3-static"].bucket_name}"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_origin_access_control" "failover" {
  name                              = "claims-failover-oac"
  description                       = "OAC for ${local.origins_by_id["failover-static"].bucket_name}"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
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
    enable_accept_encoding_brotli = true
    enable_accept_encoding_gzip   = true
  }
}

resource "aws_cloudfront_response_headers_policy" "security" {
  name = "edge-security-headers"
  security_headers_config {
    content_type_options {
      override = true
    }
    frame_options {
      frame_option = "DENY"
      override     = true
    }
    referrer_policy {
      referrer_policy = "same-origin"
      override        = true
    }
    strict_transport_security {
      access_control_max_age_sec = var.tls_policy.hsts.max_age_seconds
      include_subdomains         = var.tls_policy.hsts.include_subdomains
      preload                    = var.tls_policy.hsts.preload
      override                   = true
    }
  }
}

resource "aws_cloudfront_public_key" "signed" {
  name        = "claims-signed-downloads"
  encoded_key = file("${path.module}/signed.pem")
  comment     = "signed downloads"
}

resource "aws_cloudfront_key_group" "signed" {
  name  = "claims-signed-downloads"
  items = [aws_cloudfront_public_key.signed.id]
}

resource "aws_wafv2_web_acl" "platform" {
  name  = var.waf_policy.shared_waf_acl_name
  scope = var.waf_policy.scope

  default_action {
    allow {}
  }

  dynamic "rule" {
    for_each = var.waf_policy.managed_rule_groups
    content {
      name     = rule.value.name
      priority = rule.value.priority
      override_action {
        none {}
      }
      statement {
        managed_rule_group_statement {
          name        = rule.value.name
          vendor_name = rule.value.vendor_name
        }
      }
      visibility_config {
        cloudwatch_metrics_enabled = true
        metric_name                = rule.value.name
        sampled_requests_enabled   = true
      }
    }
  }

  dynamic "rule" {
    for_each = var.waf_policy.rate_based_rules
    content {
      name     = rule.value.name
      priority = rule.value.priority
      action {
        block {}
      }
      statement {
        rate_based_statement {
          limit              = rule.value.limit
          aggregate_key_type = rule.value.aggregate_key_type
        }
      }
      visibility_config {
        cloudwatch_metrics_enabled = true
        metric_name                = rule.value.name
        sampled_requests_enabled   = true
      }
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = var.waf_policy.shared_waf_acl_name
    sampled_requests_enabled   = true
  }
}

# static-api edge: main public entry (API, maintenance, static content).
resource "aws_cloudfront_distribution" "edge" {
  enabled             = true
  comment             = "static-api"
  default_root_object = "index.html"
  web_acl_id          = aws_wafv2_web_acl.platform.arn
  price_class         = "PriceClass_100"

  dynamic "origin" {
    for_each = toset(local.origin_ids_by_dist["static-api"])
    content {
      origin_id = origin.value
      domain_name = local.origins_by_id[origin.value].type == "s3" ? (
        origin.value == "s3-static" ? aws_s3_bucket.static.bucket_regional_domain_name : aws_s3_bucket.failover.bucket_regional_domain_name
      ) : local.origins_by_id[origin.value].domain_name

      origin_access_control_id = local.origins_by_id[origin.value].type == "s3" ? (
        origin.value == "s3-static" ? aws_cloudfront_origin_access_control.static.id : aws_cloudfront_origin_access_control.failover.id
      ) : null

      dynamic "custom_origin_config" {
        for_each = local.origins_by_id[origin.value].type == "s3" ? [] : [1]
        content {
          http_port              = 80
          https_port             = 443
          origin_protocol_policy = local.origins_by_id[origin.value].protocol_policy
          origin_ssl_protocols   = ["TLSv1.2"]
          origin_read_timeout    = 30
        }
      }

      dynamic "custom_header" {
        for_each = try([{
          name  = local.origins_by_id[origin.value].custom_header_name
          value = local.origins_by_id[origin.value].custom_header_value
        }], [])
        content {
          name  = custom_header.value.name
          value = custom_header.value.value
        }
      }
    }
  }

  default_cache_behavior {
    allowed_methods            = ["GET", "HEAD", "OPTIONS"]
    cached_methods             = ["GET", "HEAD"]
    target_origin_id           = local.fallback_origin_by_dist["static-api"]
    viewer_protocol_policy     = var.tls_policy.viewer_protocol_policy
    compress                   = true
    cache_policy_id            = "658327ea-f89d-4fab-a63d-7e88639e58f6"
    response_headers_policy_id = aws_cloudfront_response_headers_policy.security.id
  }

  dynamic "ordered_cache_behavior" {
    for_each = local.ordered_rules_by_dist["static-api"]
    content {
      path_pattern               = ordered_cache_behavior.value.path
      allowed_methods            = ordered_cache_behavior.value.allowed_methods
      cached_methods             = ["GET", "HEAD"]
      target_origin_id           = ordered_cache_behavior.value.origin_id
      viewer_protocol_policy     = var.tls_policy.viewer_protocol_policy
      compress                   = true
      cache_policy_id            = contains(["no-cache", "api-no-cache"], ordered_cache_behavior.value.cache_policy) ? aws_cloudfront_cache_policy.no_cache.id : "658327ea-f89d-4fab-a63d-7e88639e58f6"
      response_headers_policy_id = aws_cloudfront_response_headers_policy.security.id
      trusted_key_groups         = ordered_cache_behavior.value.signed ? [aws_cloudfront_key_group.signed.id] : null
    }
  }

  logging_config {
    include_cookies = local.logging_by_dist["static-api"].include_cookies
    bucket          = "${local.logging_by_dist["static-api"].bucket}.s3.amazonaws.com"
    prefix          = local.logging_by_dist["static-api"].prefix
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
    minimum_protocol_version       = var.tls_policy.minimum_protocol
  }
}

# failover edge: disaster-recovery static content, separate account/region bucket.
resource "aws_cloudfront_distribution" "failover" {
  enabled     = true
  comment     = "failover"
  web_acl_id  = aws_wafv2_web_acl.platform.arn
  price_class = "PriceClass_100"

  dynamic "origin" {
    for_each = toset(local.origin_ids_by_dist["failover"])
    content {
      origin_id = origin.value
      domain_name = local.origins_by_id[origin.value].type == "s3" ? (
        origin.value == "s3-static" ? aws_s3_bucket.static.bucket_regional_domain_name : aws_s3_bucket.failover.bucket_regional_domain_name
      ) : local.origins_by_id[origin.value].domain_name

      origin_access_control_id = local.origins_by_id[origin.value].type == "s3" ? (
        origin.value == "s3-static" ? aws_cloudfront_origin_access_control.static.id : aws_cloudfront_origin_access_control.failover.id
      ) : null

      dynamic "custom_origin_config" {
        for_each = local.origins_by_id[origin.value].type == "s3" ? [] : [1]
        content {
          http_port              = 80
          https_port             = 443
          origin_protocol_policy = local.origins_by_id[origin.value].protocol_policy
          origin_ssl_protocols   = ["TLSv1.2"]
          origin_read_timeout    = 30
        }
      }
    }
  }

  default_cache_behavior {
    allowed_methods            = ["GET", "HEAD", "OPTIONS"]
    cached_methods             = ["GET", "HEAD"]
    target_origin_id           = local.fallback_origin_by_dist["failover"]
    viewer_protocol_policy     = var.tls_policy.viewer_protocol_policy
    compress                   = true
    cache_policy_id            = "658327ea-f89d-4fab-a63d-7e88639e58f6"
    response_headers_policy_id = aws_cloudfront_response_headers_policy.security.id
  }

  dynamic "ordered_cache_behavior" {
    for_each = local.ordered_rules_by_dist["failover"]
    content {
      path_pattern               = ordered_cache_behavior.value.path
      allowed_methods            = ordered_cache_behavior.value.allowed_methods
      cached_methods             = ["GET", "HEAD"]
      target_origin_id           = ordered_cache_behavior.value.origin_id
      viewer_protocol_policy     = var.tls_policy.viewer_protocol_policy
      compress                   = true
      cache_policy_id            = contains(["no-cache", "api-no-cache"], ordered_cache_behavior.value.cache_policy) ? aws_cloudfront_cache_policy.no_cache.id : "658327ea-f89d-4fab-a63d-7e88639e58f6"
      response_headers_policy_id = aws_cloudfront_response_headers_policy.security.id
      trusted_key_groups         = ordered_cache_behavior.value.signed ? [aws_cloudfront_key_group.signed.id] : null
    }
  }

  logging_config {
    include_cookies = local.logging_by_dist["failover"].include_cookies
    bucket          = "${local.logging_by_dist["failover"].bucket}.s3.amazonaws.com"
    prefix          = local.logging_by_dist["failover"].prefix
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
    minimum_protocol_version       = var.tls_policy.minimum_protocol
  }
}

# signed_content edge: same static bucket, narrow signed exception on downloads.
resource "aws_cloudfront_distribution" "signed_content" {
  enabled     = true
  comment     = "signed-content"
  web_acl_id  = aws_wafv2_web_acl.platform.arn
  price_class = "PriceClass_100"

  dynamic "origin" {
    for_each = toset(local.origin_ids_by_dist["signed-content"])
    content {
      origin_id = origin.value
      domain_name = local.origins_by_id[origin.value].type == "s3" ? (
        origin.value == "s3-static" ? aws_s3_bucket.static.bucket_regional_domain_name : aws_s3_bucket.failover.bucket_regional_domain_name
      ) : local.origins_by_id[origin.value].domain_name

      origin_access_control_id = local.origins_by_id[origin.value].type == "s3" ? (
        origin.value == "s3-static" ? aws_cloudfront_origin_access_control.static.id : aws_cloudfront_origin_access_control.failover.id
      ) : null

      dynamic "custom_origin_config" {
        for_each = local.origins_by_id[origin.value].type == "s3" ? [] : [1]
        content {
          http_port              = 80
          https_port             = 443
          origin_protocol_policy = local.origins_by_id[origin.value].protocol_policy
          origin_ssl_protocols   = ["TLSv1.2"]
          origin_read_timeout    = 30
        }
      }
    }
  }

  default_cache_behavior {
    allowed_methods            = ["GET", "HEAD", "OPTIONS"]
    cached_methods             = ["GET", "HEAD"]
    target_origin_id           = local.fallback_origin_by_dist["signed-content"]
    viewer_protocol_policy     = var.tls_policy.viewer_protocol_policy
    compress                   = true
    cache_policy_id            = "658327ea-f89d-4fab-a63d-7e88639e58f6"
    response_headers_policy_id = aws_cloudfront_response_headers_policy.security.id
  }

  dynamic "ordered_cache_behavior" {
    for_each = local.ordered_rules_by_dist["signed-content"]
    content {
      path_pattern               = ordered_cache_behavior.value.path
      allowed_methods            = ordered_cache_behavior.value.allowed_methods
      cached_methods             = ["GET", "HEAD"]
      target_origin_id           = ordered_cache_behavior.value.origin_id
      viewer_protocol_policy     = var.tls_policy.viewer_protocol_policy
      compress                   = true
      cache_policy_id            = contains(["no-cache", "api-no-cache"], ordered_cache_behavior.value.cache_policy) ? aws_cloudfront_cache_policy.no_cache.id : "658327ea-f89d-4fab-a63d-7e88639e58f6"
      response_headers_policy_id = aws_cloudfront_response_headers_policy.security.id
      trusted_key_groups         = ordered_cache_behavior.value.signed ? [aws_cloudfront_key_group.signed.id] : null
    }
  }

  logging_config {
    include_cookies = local.logging_by_dist["signed-content"].include_cookies
    bucket          = "${local.logging_by_dist["signed-content"].bucket}.s3.amazonaws.com"
    prefix          = local.logging_by_dist["signed-content"].prefix
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
    minimum_protocol_version       = var.tls_policy.minimum_protocol
  }
}

locals {
  dist_arns = {
    "static-api"     = aws_cloudfront_distribution.edge.arn
    "failover"       = aws_cloudfront_distribution.failover.arn
    "signed-content" = aws_cloudfront_distribution.signed_content.arn
  }
}

resource "aws_s3_bucket_policy" "static" {
  bucket = aws_s3_bucket.static.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      for dist_key, arn in local.dist_arns : {
        Sid    = "Allow${replace(dist_key, "-", "_")}Static"
        Effect = "Allow"
        Principal = {
          Service = "cloudfront.amazonaws.com"
        }
        Action   = ["s3:GetObject"]
        Resource = ["${aws_s3_bucket.static.arn}/*"]
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = arn
          }
        }
      }
      if contains(local.origin_ids_by_dist[dist_key], "s3-static")
    ]
  })
}

resource "aws_s3_bucket_policy" "failover" {
  provider = aws.failover
  bucket   = aws_s3_bucket.failover.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      for dist_key, arn in local.dist_arns : {
        Sid    = "Allow${replace(dist_key, "-", "_")}Failover"
        Effect = "Allow"
        Principal = {
          Service = "cloudfront.amazonaws.com"
        }
        Action   = ["s3:GetObject"]
        Resource = ["${aws_s3_bucket.failover.arn}/*"]
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = arn
          }
        }
      }
      if contains(local.origin_ids_by_dist[dist_key], "failover-static")
    ]
  })
}

resource "aws_wafv2_web_acl_association" "dist" {
  for_each = { for k, arn in local.dist_arns : k => arn if contains(var.waf_policy.distributions, k) }

  resource_arn = each.value
  web_acl_arn  = aws_wafv2_web_acl.platform.arn
}
