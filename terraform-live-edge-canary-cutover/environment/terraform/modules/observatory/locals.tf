locals {
  probe_catalog = {
    "probe-01" = {
      id                = "probe-01"
      name              = "edge-probe-01"
      path              = "/healthz"
      method            = "GET"
      expect_status     = 200
      timeout_ms        = 1525
      region_preference = "us-west-2"
      headers           = { Host = "api.edge.example.net", X-Edge-Probe = "observatory-01", Accept = "application/json" }
      success_criteria = [
        "status == 200",
        "body_not_empty",
        "tls_hostname_match",
      ]
      failure_actions = [
        "page_oncall_if_consecutive_failures >= 3",
        "annotate_canary_timeline",
      ]
    }
    "probe-02" = {
      id                = "probe-02"
      name              = "edge-probe-02"
      path              = "/v1/status"
      method            = "GET"
      expect_status     = 200
      timeout_ms        = 1550
      region_preference = "eu-west-1"
      headers           = { Host = "api.edge.example.net", X-Edge-Probe = "observatory-02", Accept = "application/json" }
      success_criteria = [
        "status == 200",
        "body_not_empty",
        "tls_hostname_match",
      ]
      failure_actions = [
        "page_oncall_if_consecutive_failures >= 3",
        "annotate_canary_timeline",
      ]
    }
    "probe-03" = {
      id                = "probe-03"
      name              = "edge-probe-03"
      path              = "/v1/ready"
      method            = "GET"
      expect_status     = 200
      timeout_ms        = 1575
      region_preference = "us-east-1"
      headers           = { Host = "api.edge.example.net", X-Edge-Probe = "observatory-03", Accept = "application/json" }
      success_criteria = [
        "status == 200",
        "body_not_empty",
        "tls_hostname_match",
      ]
      failure_actions = [
        "page_oncall_if_consecutive_failures >= 3",
        "annotate_canary_timeline",
      ]
    }
    "probe-04" = {
      id                = "probe-04"
      name              = "edge-probe-04"
      path              = "/api/v1/catalog"
      method            = "GET"
      expect_status     = 200
      timeout_ms        = 1600
      region_preference = "us-west-2"
      headers           = { Host = "api.edge.example.net", X-Edge-Probe = "observatory-04", Accept = "application/json" }
      success_criteria = [
        "status == 200",
        "body_not_empty",
        "tls_hostname_match",
      ]
      failure_actions = [
        "page_oncall_if_consecutive_failures >= 3",
        "annotate_canary_timeline",
      ]
    }
    "probe-05" = {
      id                = "probe-05"
      name              = "edge-probe-05"
      path              = "/api/v1/catalog?limit=10"
      method            = "GET"
      expect_status     = 200
      timeout_ms        = 1625
      region_preference = "eu-west-1"
      headers           = { Host = "api.edge.example.net", X-Edge-Probe = "observatory-05", Accept = "application/json" }
      success_criteria = [
        "status == 200",
        "body_not_empty",
        "tls_hostname_match",
      ]
      failure_actions = [
        "page_oncall_if_consecutive_failures >= 3",
        "annotate_canary_timeline",
      ]
    }
    "probe-06" = {
      id                = "probe-06"
      name              = "edge-probe-06"
      path              = "/api/v1/orders"
      method            = "GET"
      expect_status     = 200
      timeout_ms        = 1650
      region_preference = "us-east-1"
      headers           = { Host = "api.edge.example.net", X-Edge-Probe = "observatory-06", Accept = "application/json" }
      success_criteria = [
        "status == 200",
        "body_not_empty",
        "tls_hostname_match",
      ]
      failure_actions = [
        "page_oncall_if_consecutive_failures >= 3",
        "annotate_canary_timeline",
      ]
    }
    "probe-07" = {
      id                = "probe-07"
      name              = "edge-probe-07"
      path              = "/api/v1/orders"
      method            = "POST"
      expect_status     = 201
      timeout_ms        = 1675
      region_preference = "us-west-2"
      headers           = { Host = "api.edge.example.net", X-Edge-Probe = "observatory-07", Accept = "application/json" }
      success_criteria = [
        "status == 201",
        "body_not_empty",
        "tls_hostname_match",
      ]
      failure_actions = [
        "page_oncall_if_consecutive_failures >= 3",
        "annotate_canary_timeline",
      ]
    }
    "probe-08" = {
      id                = "probe-08"
      name              = "edge-probe-08"
      path              = "/api/v1/orders/probe-1"
      method            = "GET"
      expect_status     = 200
      timeout_ms        = 1700
      region_preference = "eu-west-1"
      headers           = { Host = "api.edge.example.net", X-Edge-Probe = "observatory-08", Accept = "application/json" }
      success_criteria = [
        "status == 200",
        "body_not_empty",
        "tls_hostname_match",
      ]
      failure_actions = [
        "page_oncall_if_consecutive_failures >= 3",
        "annotate_canary_timeline",
      ]
    }
    "probe-09" = {
      id                = "probe-09"
      name              = "edge-probe-09"
      path              = "/api/v1/payments/intent"
      method            = "POST"
      expect_status     = 200
      timeout_ms        = 1725
      region_preference = "us-east-1"
      headers           = { Host = "api.edge.example.net", X-Edge-Probe = "observatory-09", Accept = "application/json" }
      success_criteria = [
        "status == 200",
        "body_not_empty",
        "tls_hostname_match",
      ]
      failure_actions = [
        "page_oncall_if_consecutive_failures >= 3",
        "annotate_canary_timeline",
      ]
    }
    "probe-10" = {
      id                = "probe-10"
      name              = "edge-probe-10"
      path              = "/api/v1/users/me"
      method            = "GET"
      expect_status     = 200
      timeout_ms        = 1750
      region_preference = "us-west-2"
      headers           = { Host = "api.edge.example.net", X-Edge-Probe = "observatory-10", Accept = "application/json" }
      success_criteria = [
        "status == 200",
        "body_not_empty",
        "tls_hostname_match",
      ]
      failure_actions = [
        "page_oncall_if_consecutive_failures >= 3",
        "annotate_canary_timeline",
      ]
    }
    "probe-11" = {
      id                = "probe-11"
      name              = "edge-probe-11"
      path              = "/api/v1/search?q=edge"
      method            = "GET"
      expect_status     = 200
      timeout_ms        = 1775
      region_preference = "eu-west-1"
      headers           = { Host = "api.edge.example.net", X-Edge-Probe = "observatory-11", Accept = "application/json" }
      success_criteria = [
        "status == 200",
        "body_not_empty",
        "tls_hostname_match",
      ]
      failure_actions = [
        "page_oncall_if_consecutive_failures >= 3",
        "annotate_canary_timeline",
      ]
    }
    "probe-12" = {
      id                = "probe-12"
      name              = "edge-probe-12"
      path              = "/api/v1/metrics/scrape"
      method            = "GET"
      expect_status     = 200
      timeout_ms        = 1800
      region_preference = "us-east-1"
      headers           = { Host = "api.edge.example.net", X-Edge-Probe = "observatory-12", Accept = "application/json" }
      success_criteria = [
        "status == 200",
        "body_not_empty",
        "tls_hostname_match",
      ]
      failure_actions = [
        "page_oncall_if_consecutive_failures >= 3",
        "annotate_canary_timeline",
      ]
    }
    "probe-13" = {
      id                = "probe-13"
      name              = "edge-probe-13"
      path              = "/api/v1/geo/nearest"
      method            = "GET"
      expect_status     = 200
      timeout_ms        = 1825
      region_preference = "us-west-2"
      headers           = { Host = "api.edge.example.net", X-Edge-Probe = "observatory-13", Accept = "application/json" }
      success_criteria = [
        "status == 200",
        "body_not_empty",
        "tls_hostname_match",
      ]
      failure_actions = [
        "page_oncall_if_consecutive_failures >= 3",
        "annotate_canary_timeline",
      ]
    }
    "probe-14" = {
      id                = "probe-14"
      name              = "edge-probe-14"
      path              = "/api/v1/cdn/purge-dry-run"
      method            = "POST"
      expect_status     = 200
      timeout_ms        = 1850
      region_preference = "eu-west-1"
      headers           = { Host = "api.edge.example.net", X-Edge-Probe = "observatory-14", Accept = "application/json" }
      success_criteria = [
        "status == 200",
        "body_not_empty",
        "tls_hostname_match",
      ]
      failure_actions = [
        "page_oncall_if_consecutive_failures >= 3",
        "annotate_canary_timeline",
      ]
    }
    "probe-15" = {
      id                = "probe-15"
      name              = "edge-probe-15"
      path              = "/api/v1/auth/session"
      method            = "GET"
      expect_status     = 200
      timeout_ms        = 1875
      region_preference = "us-east-1"
      headers           = { Host = "api.edge.example.net", X-Edge-Probe = "observatory-15", Accept = "application/json" }
      success_criteria = [
        "status == 200",
        "body_not_empty",
        "tls_hostname_match",
      ]
      failure_actions = [
        "page_oncall_if_consecutive_failures >= 3",
        "annotate_canary_timeline",
      ]
    }
    "probe-16" = {
      id                = "probe-16"
      name              = "edge-probe-16"
      path              = "/api/v1/auth/refresh"
      method            = "POST"
      expect_status     = 200
      timeout_ms        = 1900
      region_preference = "us-west-2"
      headers           = { Host = "api.edge.example.net", X-Edge-Probe = "observatory-16", Accept = "application/json" }
      success_criteria = [
        "status == 200",
        "body_not_empty",
        "tls_hostname_match",
      ]
      failure_actions = [
        "page_oncall_if_consecutive_failures >= 3",
        "annotate_canary_timeline",
      ]
    }
    "probe-17" = {
      id                = "probe-17"
      name              = "edge-probe-17"
      path              = "/api/v1/feature-flags"
      method            = "GET"
      expect_status     = 200
      timeout_ms        = 1925
      region_preference = "eu-west-1"
      headers           = { Host = "api.edge.example.net", X-Edge-Probe = "observatory-17", Accept = "application/json" }
      success_criteria = [
        "status == 200",
        "body_not_empty",
        "tls_hostname_match",
      ]
      failure_actions = [
        "page_oncall_if_consecutive_failures >= 3",
        "annotate_canary_timeline",
      ]
    }
    "probe-18" = {
      id                = "probe-18"
      name              = "edge-probe-18"
      path              = "/api/v1/webhooks/ping"
      method            = "POST"
      expect_status     = 200
      timeout_ms        = 1950
      region_preference = "us-east-1"
      headers           = { Host = "api.edge.example.net", X-Edge-Probe = "observatory-18", Accept = "application/json" }
      success_criteria = [
        "status == 200",
        "body_not_empty",
        "tls_hostname_match",
      ]
      failure_actions = [
        "page_oncall_if_consecutive_failures >= 3",
        "annotate_canary_timeline",
      ]
    }
    "probe-19" = {
      id                = "probe-19"
      name              = "edge-probe-19"
      path              = "/static/robots.txt"
      method            = "GET"
      expect_status     = 200
      timeout_ms        = 1975
      region_preference = "us-west-2"
      headers           = { Host = "api.edge.example.net", X-Edge-Probe = "observatory-19", Accept = "application/json" }
      success_criteria = [
        "status == 200",
        "body_not_empty",
        "tls_hostname_match",
      ]
      failure_actions = [
        "page_oncall_if_consecutive_failures >= 3",
        "annotate_canary_timeline",
      ]
    }
    "probe-20" = {
      id                = "probe-20"
      name              = "edge-probe-20"
      path              = "/static/favicon.ico"
      method            = "GET"
      expect_status     = 200
      timeout_ms        = 2000
      region_preference = "eu-west-1"
      headers           = { Host = "api.edge.example.net", X-Edge-Probe = "observatory-20", Accept = "application/json" }
      success_criteria = [
        "status == 200",
        "body_not_empty",
        "tls_hostname_match",
      ]
      failure_actions = [
        "page_oncall_if_consecutive_failures >= 3",
        "annotate_canary_timeline",
      ]
    }
  }

  probes_by_id = {
    for p in var.probes : p.id => p
  }

  probe_files = {
    for id, p in local.probes_by_id : id => "${var.output_dir}/${id}.json"
  }

  index_document = {
    engagement  = var.engagement
    hostname    = var.hostname
    dns_fqdn    = var.dns_fqdn
    green_pool  = var.green_pool
    probe_ids   = [for p in var.probes : p.id]
    probe_count = length(var.probes)
  }
}
