locals {
  healthcheck_profiles = {
    "http-shallow" = {
      protocol            = "http"
      path                = "/"
      expect_status       = 200
      timeout_ms          = 1000
      unhealthy_threshold = 3
      healthy_threshold   = 5
      interval_ms         = 1500
      follow_redirects    = false
      verify_tls          = false
    }
    "http-deep" = {
      protocol            = "http"
      path                = "/healthz"
      expect_status       = 200
      timeout_ms          = 1500
      unhealthy_threshold = 3
      healthy_threshold   = 10
      interval_ms         = 2000
      follow_redirects    = false
      verify_tls          = false
    }
    "https-shallow" = {
      protocol            = "https"
      path                = "/"
      expect_status       = 200
      timeout_ms          = 1000
      unhealthy_threshold = 3
      healthy_threshold   = 5
      interval_ms         = 1500
      follow_redirects    = false
      verify_tls          = true
    }
    "https-deep" = {
      protocol            = "https"
      path                = "/v1/ready"
      expect_status       = 200
      timeout_ms          = 2000
      unhealthy_threshold = 2
      healthy_threshold   = 10
      interval_ms         = 2500
      follow_redirects    = false
      verify_tls          = true
    }
    "tcp-connect" = {
      protocol            = "tcp"
      path                = ""
      expect_status       = 0
      timeout_ms          = 500
      unhealthy_threshold = 5
      healthy_threshold   = 5
      interval_ms         = 1000
      follow_redirects    = false
      verify_tls          = false
    }
    "tls-handshake" = {
      protocol            = "tls"
      path                = ""
      expect_status       = 0
      timeout_ms          = 800
      unhealthy_threshold = 3
      healthy_threshold   = 5
      interval_ms         = 1300
      follow_redirects    = false
      verify_tls          = true
    }
    "grpc-health" = {
      protocol            = "grpc"
      path                = "/grpc.health.v1.Health/Check"
      expect_status       = 0
      timeout_ms          = 1200
      unhealthy_threshold = 2
      healthy_threshold   = 8
      interval_ms         = 1700
      follow_redirects    = false
      verify_tls          = false
    }
    "http-canary-header" = {
      protocol            = "http"
      path                = "/v1/status"
      expect_status       = 200
      timeout_ms          = 1500
      unhealthy_threshold = 3
      healthy_threshold   = 5
      interval_ms         = 2000
      follow_redirects    = false
      verify_tls          = false
    }
  }

  origin_port_policy = {
    80    = { allowed_protocols = ["http"], notes = "Cleartext only on lab overlays." }
    8080  = { allowed_protocols = ["http"], notes = "Blue pool default listener." }
    8443  = { allowed_protocols = ["https", "tls"], notes = "Green pool default listener." }
    443   = { allowed_protocols = ["https", "tls"], notes = "Public edge termination — not origin." }
    9090  = { allowed_protocols = ["http"], notes = "Metrics scrape sidecar." }
    50051 = { allowed_protocols = ["grpc"], notes = "gRPC health channel." }
  }

  blue_origin_enriched = {
    "origin-blue-01" = {
      id          = "origin-blue-01"
      host        = "10.10.1.10"
      port        = 8080
      healthy     = true
      weight      = 100
      protocol    = "http"
      region_hint = "us-east-1"
      healthcheck = "http-deep"
      drain_score = 0
      labels = {
        color       = "blue"
        engagement  = var.engagement
        pool_id     = var.blue_pool.id
        origin_id   = "origin-blue-01"
      }
    }
    "origin-blue-02" = {
      id          = "origin-blue-02"
      host        = "10.10.2.10"
      port        = 8080
      healthy     = true
      weight      = 100
      protocol    = "http"
      region_hint = "us-east-1"
      healthcheck = "http-deep"
      drain_score = 0
      labels = {
        color       = "blue"
        engagement  = var.engagement
        pool_id     = var.blue_pool.id
        origin_id   = "origin-blue-02"
      }
    }
    "origin-blue-03" = {
      id          = "origin-blue-03"
      host        = "10.10.3.10"
      port        = 8080
      healthy     = true
      weight      = 100
      protocol    = "http"
      region_hint = "us-east-1"
      healthcheck = "http-deep"
      drain_score = 0
      labels = {
        color       = "blue"
        engagement  = var.engagement
        pool_id     = var.blue_pool.id
        origin_id   = "origin-blue-03"
      }
    }
    "origin-blue-04" = {
      id          = "origin-blue-04"
      host        = "10.10.4.10"
      port        = 8080
      healthy     = true
      weight      = 100
      protocol    = "http"
      region_hint = "us-east-1"
      healthcheck = "http-deep"
      drain_score = 0
      labels = {
        color       = "blue"
        engagement  = var.engagement
        pool_id     = var.blue_pool.id
        origin_id   = "origin-blue-04"
      }
    }
    "origin-blue-05" = {
      id          = "origin-blue-05"
      host        = "10.10.5.10"
      port        = 8080
      healthy     = true
      weight      = 100
      protocol    = "http"
      region_hint = "us-west-2"
      healthcheck = "http-deep"
      drain_score = 0
      labels = {
        color       = "blue"
        engagement  = var.engagement
        pool_id     = var.blue_pool.id
        origin_id   = "origin-blue-05"
      }
    }
    "origin-blue-06" = {
      id          = "origin-blue-06"
      host        = "10.10.6.10"
      port        = 8080
      healthy     = true
      weight      = 100
      protocol    = "http"
      region_hint = "us-west-2"
      healthcheck = "http-deep"
      drain_score = 0
      labels = {
        color       = "blue"
        engagement  = var.engagement
        pool_id     = var.blue_pool.id
        origin_id   = "origin-blue-06"
      }
    }
    "origin-blue-07" = {
      id          = "origin-blue-07"
      host        = "10.10.7.10"
      port        = 8080
      healthy     = true
      weight      = 100
      protocol    = "http"
      region_hint = "us-west-2"
      healthcheck = "http-deep"
      drain_score = 0
      labels = {
        color       = "blue"
        engagement  = var.engagement
        pool_id     = var.blue_pool.id
        origin_id   = "origin-blue-07"
      }
    }
    "origin-blue-08" = {
      id          = "origin-blue-08"
      host        = "10.10.8.10"
      port        = 8080
      healthy     = true
      weight      = 100
      protocol    = "http"
      region_hint = "us-west-2"
      healthcheck = "http-deep"
      drain_score = 0
      labels = {
        color       = "blue"
        engagement  = var.engagement
        pool_id     = var.blue_pool.id
        origin_id   = "origin-blue-08"
      }
    }
    "origin-blue-09" = {
      id          = "origin-blue-09"
      host        = "10.10.9.10"
      port        = 8080
      healthy     = true
      weight      = 100
      protocol    = "http"
      region_hint = "eu-west-1"
      healthcheck = "http-deep"
      drain_score = 0
      labels = {
        color       = "blue"
        engagement  = var.engagement
        pool_id     = var.blue_pool.id
        origin_id   = "origin-blue-09"
      }
    }
    "origin-blue-10" = {
      id          = "origin-blue-10"
      host        = "10.10.10.10"
      port        = 8080
      healthy     = true
      weight      = 100
      protocol    = "http"
      region_hint = "eu-west-1"
      healthcheck = "http-deep"
      drain_score = 0
      labels = {
        color       = "blue"
        engagement  = var.engagement
        pool_id     = var.blue_pool.id
        origin_id   = "origin-blue-10"
      }
    }
  }

  green_origin_enriched = {
    "origin-green-01" = {
      id          = "origin-green-01"
      host        = "10.20.1.10"
      port        = 8443
      healthy     = true
      weight      = 100
      protocol    = "https"
      region_hint = "us-east-1"
      healthcheck = "https-deep"
      drain_score = 0
      labels = {
        color       = "green"
        engagement  = var.engagement
        pool_id     = var.green_pool.id
        origin_id   = "origin-green-01"
      }
    }
    "origin-green-02" = {
      id          = "origin-green-02"
      host        = "10.20.2.10"
      port        = 8443
      healthy     = true
      weight      = 100
      protocol    = "https"
      region_hint = "us-east-1"
      healthcheck = "https-deep"
      drain_score = 0
      labels = {
        color       = "green"
        engagement  = var.engagement
        pool_id     = var.green_pool.id
        origin_id   = "origin-green-02"
      }
    }
    "origin-green-03" = {
      id          = "origin-green-03"
      host        = "10.20.3.10"
      port        = 8443
      healthy     = true
      weight      = 100
      protocol    = "https"
      region_hint = "us-east-1"
      healthcheck = "https-deep"
      drain_score = 0
      labels = {
        color       = "green"
        engagement  = var.engagement
        pool_id     = var.green_pool.id
        origin_id   = "origin-green-03"
      }
    }
    "origin-green-04" = {
      id          = "origin-green-04"
      host        = "10.20.4.10"
      port        = 8443
      healthy     = true
      weight      = 100
      protocol    = "https"
      region_hint = "us-east-1"
      healthcheck = "https-deep"
      drain_score = 0
      labels = {
        color       = "green"
        engagement  = var.engagement
        pool_id     = var.green_pool.id
        origin_id   = "origin-green-04"
      }
    }
    "origin-green-05" = {
      id          = "origin-green-05"
      host        = "10.20.5.10"
      port        = 8443
      healthy     = true
      weight      = 100
      protocol    = "https"
      region_hint = "us-west-2"
      healthcheck = "https-deep"
      drain_score = 0
      labels = {
        color       = "green"
        engagement  = var.engagement
        pool_id     = var.green_pool.id
        origin_id   = "origin-green-05"
      }
    }
    "origin-green-06" = {
      id          = "origin-green-06"
      host        = "10.20.6.10"
      port        = 8443
      healthy     = true
      weight      = 100
      protocol    = "https"
      region_hint = "us-west-2"
      healthcheck = "https-deep"
      drain_score = 0
      labels = {
        color       = "green"
        engagement  = var.engagement
        pool_id     = var.green_pool.id
        origin_id   = "origin-green-06"
      }
    }
    "origin-green-07" = {
      id          = "origin-green-07"
      host        = "10.20.7.10"
      port        = 8443
      healthy     = true
      weight      = 100
      protocol    = "https"
      region_hint = "us-west-2"
      healthcheck = "https-deep"
      drain_score = 0
      labels = {
        color       = "green"
        engagement  = var.engagement
        pool_id     = var.green_pool.id
        origin_id   = "origin-green-07"
      }
    }
    "origin-green-08" = {
      id          = "origin-green-08"
      host        = "10.20.8.10"
      port        = 8443
      healthy     = true
      weight      = 100
      protocol    = "https"
      region_hint = "us-west-2"
      healthcheck = "https-deep"
      drain_score = 0
      labels = {
        color       = "green"
        engagement  = var.engagement
        pool_id     = var.green_pool.id
        origin_id   = "origin-green-08"
      }
    }
    "origin-green-09" = {
      id          = "origin-green-09"
      host        = "10.20.9.10"
      port        = 8443
      healthy     = true
      weight      = 100
      protocol    = "https"
      region_hint = "eu-west-1"
      healthcheck = "https-deep"
      drain_score = 0
      labels = {
        color       = "green"
        engagement  = var.engagement
        pool_id     = var.green_pool.id
        origin_id   = "origin-green-09"
      }
    }
    "origin-green-10" = {
      id          = "origin-green-10"
      host        = "10.20.10.10"
      port        = 8443
      healthy     = true
      weight      = 100
      protocol    = "https"
      region_hint = "eu-west-1"
      healthcheck = "https-deep"
      drain_score = 0
      labels = {
        color       = "green"
        engagement  = var.engagement
        pool_id     = var.green_pool.id
        origin_id   = "origin-green-10"
      }
    }
  }

  blue_api_origins = [
    for o in var.blue_pool.origins : {
      id      = o.id
      host    = o.host
      port    = o.port
      healthy = o.healthy
    }
  ]

  green_api_origins = [
    for o in var.green_pool.origins : {
      id      = o.id
      host    = o.host
      port    = o.port
      healthy = o.healthy
    }
  ]

  blue_healthy_count  = length([for o in var.blue_pool.origins : o if o.healthy])
  green_healthy_count = length([for o in var.green_pool.origins : o if o.healthy])

  blue_meets_floor  = local.blue_healthy_count >= var.blue_pool.min_healthy
  green_meets_floor = local.green_healthy_count >= var.green_pool.min_healthy

  blue_body = {
    id          = var.blue_pool.id
    network_id  = var.blue_pool.network_id
    color       = "blue"
    min_healthy = var.blue_pool.min_healthy
    origins     = local.blue_api_origins
  }

  green_body = {
    id          = var.green_pool.id
    network_id  = var.green_pool.network_id
    color       = "green"
    min_healthy = var.green_pool.min_healthy
    origins     = local.green_api_origins
  }

  blue_marker  = sha256(jsonencode(local.blue_body))
  green_marker = sha256(jsonencode(local.green_body))

  blue_payload_path  = "${var.payload_dir}/${var.blue_pool.id}.json"
  green_payload_path = "${var.payload_dir}/${var.green_pool.id}.json"
}
