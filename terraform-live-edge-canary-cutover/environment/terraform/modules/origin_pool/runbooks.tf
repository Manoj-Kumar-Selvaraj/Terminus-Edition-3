locals {
  origin_runbooks = {
    "origin-blue-01" = {
      pool_color = "blue"
      replace_with = "spin replacement behind pool-blue-edge-primary then drain origin-blue-01"
      page_on_failure = false
      verification_steps = [
        "curl -fsS http://10.10.1.10:8080/healthz",
        "confirm healthy=true in GET /v1/snapshot pools.pool-blue-edge-primary",
        "ensure min_healthy still satisfied after drain",
      ]
      blast_radius = [
        "canary_route depends on pool-blue-edge-primary health",
        "dns_cutover requires green healthy when targeting green",
      ]
    }
    "origin-blue-02" = {
      pool_color = "blue"
      replace_with = "spin replacement behind pool-blue-edge-primary then drain origin-blue-02"
      page_on_failure = false
      verification_steps = [
        "curl -fsS http://10.10.2.10:8080/healthz",
        "confirm healthy=true in GET /v1/snapshot pools.pool-blue-edge-primary",
        "ensure min_healthy still satisfied after drain",
      ]
      blast_radius = [
        "canary_route depends on pool-blue-edge-primary health",
        "dns_cutover requires green healthy when targeting green",
      ]
    }
    "origin-blue-03" = {
      pool_color = "blue"
      replace_with = "spin replacement behind pool-blue-edge-primary then drain origin-blue-03"
      page_on_failure = false
      verification_steps = [
        "curl -fsS http://10.10.3.10:8080/healthz",
        "confirm healthy=true in GET /v1/snapshot pools.pool-blue-edge-primary",
        "ensure min_healthy still satisfied after drain",
      ]
      blast_radius = [
        "canary_route depends on pool-blue-edge-primary health",
        "dns_cutover requires green healthy when targeting green",
      ]
    }
    "origin-blue-04" = {
      pool_color = "blue"
      replace_with = "spin replacement behind pool-blue-edge-primary then drain origin-blue-04"
      page_on_failure = false
      verification_steps = [
        "curl -fsS http://10.10.4.10:8080/healthz",
        "confirm healthy=true in GET /v1/snapshot pools.pool-blue-edge-primary",
        "ensure min_healthy still satisfied after drain",
      ]
      blast_radius = [
        "canary_route depends on pool-blue-edge-primary health",
        "dns_cutover requires green healthy when targeting green",
      ]
    }
    "origin-blue-05" = {
      pool_color = "blue"
      replace_with = "spin replacement behind pool-blue-edge-primary then drain origin-blue-05"
      page_on_failure = false
      verification_steps = [
        "curl -fsS http://10.10.5.10:8080/healthz",
        "confirm healthy=true in GET /v1/snapshot pools.pool-blue-edge-primary",
        "ensure min_healthy still satisfied after drain",
      ]
      blast_radius = [
        "canary_route depends on pool-blue-edge-primary health",
        "dns_cutover requires green healthy when targeting green",
      ]
    }
    "origin-blue-06" = {
      pool_color = "blue"
      replace_with = "spin replacement behind pool-blue-edge-primary then drain origin-blue-06"
      page_on_failure = false
      verification_steps = [
        "curl -fsS http://10.10.6.10:8080/healthz",
        "confirm healthy=true in GET /v1/snapshot pools.pool-blue-edge-primary",
        "ensure min_healthy still satisfied after drain",
      ]
      blast_radius = [
        "canary_route depends on pool-blue-edge-primary health",
        "dns_cutover requires green healthy when targeting green",
      ]
    }
    "origin-blue-07" = {
      pool_color = "blue"
      replace_with = "spin replacement behind pool-blue-edge-primary then drain origin-blue-07"
      page_on_failure = false
      verification_steps = [
        "curl -fsS http://10.10.7.10:8080/healthz",
        "confirm healthy=true in GET /v1/snapshot pools.pool-blue-edge-primary",
        "ensure min_healthy still satisfied after drain",
      ]
      blast_radius = [
        "canary_route depends on pool-blue-edge-primary health",
        "dns_cutover requires green healthy when targeting green",
      ]
    }
    "origin-blue-08" = {
      pool_color = "blue"
      replace_with = "spin replacement behind pool-blue-edge-primary then drain origin-blue-08"
      page_on_failure = false
      verification_steps = [
        "curl -fsS http://10.10.8.10:8080/healthz",
        "confirm healthy=true in GET /v1/snapshot pools.pool-blue-edge-primary",
        "ensure min_healthy still satisfied after drain",
      ]
      blast_radius = [
        "canary_route depends on pool-blue-edge-primary health",
        "dns_cutover requires green healthy when targeting green",
      ]
    }
    "origin-blue-09" = {
      pool_color = "blue"
      replace_with = "spin replacement behind pool-blue-edge-primary then drain origin-blue-09"
      page_on_failure = false
      verification_steps = [
        "curl -fsS http://10.10.9.10:8080/healthz",
        "confirm healthy=true in GET /v1/snapshot pools.pool-blue-edge-primary",
        "ensure min_healthy still satisfied after drain",
      ]
      blast_radius = [
        "canary_route depends on pool-blue-edge-primary health",
        "dns_cutover requires green healthy when targeting green",
      ]
    }
    "origin-blue-10" = {
      pool_color = "blue"
      replace_with = "spin replacement behind pool-blue-edge-primary then drain origin-blue-10"
      page_on_failure = false
      verification_steps = [
        "curl -fsS http://10.10.10.10:8080/healthz",
        "confirm healthy=true in GET /v1/snapshot pools.pool-blue-edge-primary",
        "ensure min_healthy still satisfied after drain",
      ]
      blast_radius = [
        "canary_route depends on pool-blue-edge-primary health",
        "dns_cutover requires green healthy when targeting green",
      ]
    }
    "origin-green-01" = {
      pool_color = "green"
      replace_with = "spin replacement behind pool-green-edge-canary then drain origin-green-01"
      page_on_failure = true
      verification_steps = [
        "curl -fsS http://10.20.1.10:8443/healthz",
        "confirm healthy=true in GET /v1/snapshot pools.pool-green-edge-canary",
        "ensure min_healthy still satisfied after drain",
      ]
      blast_radius = [
        "canary_route depends on pool-green-edge-canary health",
        "dns_cutover requires green healthy when targeting green",
      ]
    }
    "origin-green-02" = {
      pool_color = "green"
      replace_with = "spin replacement behind pool-green-edge-canary then drain origin-green-02"
      page_on_failure = true
      verification_steps = [
        "curl -fsS http://10.20.2.10:8443/healthz",
        "confirm healthy=true in GET /v1/snapshot pools.pool-green-edge-canary",
        "ensure min_healthy still satisfied after drain",
      ]
      blast_radius = [
        "canary_route depends on pool-green-edge-canary health",
        "dns_cutover requires green healthy when targeting green",
      ]
    }
    "origin-green-03" = {
      pool_color = "green"
      replace_with = "spin replacement behind pool-green-edge-canary then drain origin-green-03"
      page_on_failure = true
      verification_steps = [
        "curl -fsS http://10.20.3.10:8443/healthz",
        "confirm healthy=true in GET /v1/snapshot pools.pool-green-edge-canary",
        "ensure min_healthy still satisfied after drain",
      ]
      blast_radius = [
        "canary_route depends on pool-green-edge-canary health",
        "dns_cutover requires green healthy when targeting green",
      ]
    }
    "origin-green-04" = {
      pool_color = "green"
      replace_with = "spin replacement behind pool-green-edge-canary then drain origin-green-04"
      page_on_failure = true
      verification_steps = [
        "curl -fsS http://10.20.4.10:8443/healthz",
        "confirm healthy=true in GET /v1/snapshot pools.pool-green-edge-canary",
        "ensure min_healthy still satisfied after drain",
      ]
      blast_radius = [
        "canary_route depends on pool-green-edge-canary health",
        "dns_cutover requires green healthy when targeting green",
      ]
    }
    "origin-green-05" = {
      pool_color = "green"
      replace_with = "spin replacement behind pool-green-edge-canary then drain origin-green-05"
      page_on_failure = true
      verification_steps = [
        "curl -fsS http://10.20.5.10:8443/healthz",
        "confirm healthy=true in GET /v1/snapshot pools.pool-green-edge-canary",
        "ensure min_healthy still satisfied after drain",
      ]
      blast_radius = [
        "canary_route depends on pool-green-edge-canary health",
        "dns_cutover requires green healthy when targeting green",
      ]
    }
    "origin-green-06" = {
      pool_color = "green"
      replace_with = "spin replacement behind pool-green-edge-canary then drain origin-green-06"
      page_on_failure = true
      verification_steps = [
        "curl -fsS http://10.20.6.10:8443/healthz",
        "confirm healthy=true in GET /v1/snapshot pools.pool-green-edge-canary",
        "ensure min_healthy still satisfied after drain",
      ]
      blast_radius = [
        "canary_route depends on pool-green-edge-canary health",
        "dns_cutover requires green healthy when targeting green",
      ]
    }
    "origin-green-07" = {
      pool_color = "green"
      replace_with = "spin replacement behind pool-green-edge-canary then drain origin-green-07"
      page_on_failure = true
      verification_steps = [
        "curl -fsS http://10.20.7.10:8443/healthz",
        "confirm healthy=true in GET /v1/snapshot pools.pool-green-edge-canary",
        "ensure min_healthy still satisfied after drain",
      ]
      blast_radius = [
        "canary_route depends on pool-green-edge-canary health",
        "dns_cutover requires green healthy when targeting green",
      ]
    }
    "origin-green-08" = {
      pool_color = "green"
      replace_with = "spin replacement behind pool-green-edge-canary then drain origin-green-08"
      page_on_failure = true
      verification_steps = [
        "curl -fsS http://10.20.8.10:8443/healthz",
        "confirm healthy=true in GET /v1/snapshot pools.pool-green-edge-canary",
        "ensure min_healthy still satisfied after drain",
      ]
      blast_radius = [
        "canary_route depends on pool-green-edge-canary health",
        "dns_cutover requires green healthy when targeting green",
      ]
    }
    "origin-green-09" = {
      pool_color = "green"
      replace_with = "spin replacement behind pool-green-edge-canary then drain origin-green-09"
      page_on_failure = true
      verification_steps = [
        "curl -fsS http://10.20.9.10:8443/healthz",
        "confirm healthy=true in GET /v1/snapshot pools.pool-green-edge-canary",
        "ensure min_healthy still satisfied after drain",
      ]
      blast_radius = [
        "canary_route depends on pool-green-edge-canary health",
        "dns_cutover requires green healthy when targeting green",
      ]
    }
    "origin-green-10" = {
      pool_color = "green"
      replace_with = "spin replacement behind pool-green-edge-canary then drain origin-green-10"
      page_on_failure = true
      verification_steps = [
        "curl -fsS http://10.20.10.10:8443/healthz",
        "confirm healthy=true in GET /v1/snapshot pools.pool-green-edge-canary",
        "ensure min_healthy still satisfied after drain",
      ]
      blast_radius = [
        "canary_route depends on pool-green-edge-canary health",
        "dns_cutover requires green healthy when targeting green",
      ]
    }
  }
}
