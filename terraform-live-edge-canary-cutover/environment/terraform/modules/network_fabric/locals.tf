locals {
  region_catalog = {
    "us-east-1" = {
      continent           = "na"
      provider_code       = "aws"
      latency_class       = "core"
      dns_anycast_pref    = 10
      supported_tiers     = ["edge-ingress", "origin-mesh", "disaster-recovery"]
      compliance_regimes  = ["soc2", "pci-dss"]
      default_mtu         = 9001
      bgp_asn_hint        = 64512
      time_zone           = "America/New_York"
      edge_pop_codes      = ["IAD", "EWR", "ATL"]
    }
    "us-west-2" = {
      continent           = "na"
      provider_code       = "aws"
      latency_class       = "core"
      dns_anycast_pref    = 20
      supported_tiers     = ["edge-ingress", "origin-mesh"]
      compliance_regimes  = ["soc2"]
      default_mtu         = 9001
      bgp_asn_hint        = 64513
      time_zone           = "America/Los_Angeles"
      edge_pop_codes      = ["PDX", "SFO", "SEA"]
    }
    "eu-west-1" = {
      continent           = "eu"
      provider_code       = "aws"
      latency_class       = "core"
      dns_anycast_pref    = 30
      supported_tiers     = ["origin-mesh", "disaster-recovery"]
      compliance_regimes  = ["soc2", "gdpr"]
      default_mtu         = 1500
      bgp_asn_hint        = 64514
      time_zone           = "Europe/Dublin"
      edge_pop_codes      = ["DUB", "LHR", "AMS"]
    }
    "ap-southeast-1" = {
      continent           = "apac"
      provider_code       = "aws"
      latency_class       = "extended"
      dns_anycast_pref    = 40
      supported_tiers     = ["origin-mesh"]
      compliance_regimes  = ["soc2"]
      default_mtu         = 1500
      bgp_asn_hint        = 64515
      time_zone           = "Asia/Singapore"
      edge_pop_codes      = ["SIN", "HKG", "NRT"]
    }
    "sa-east-1" = {
      continent           = "sa"
      provider_code       = "aws"
      latency_class       = "extended"
      dns_anycast_pref    = 50
      supported_tiers     = ["disaster-recovery"]
      compliance_regimes  = ["soc2"]
      default_mtu         = 1500
      bgp_asn_hint        = 64516
      time_zone           = "America/Sao_Paulo"
      edge_pop_codes      = ["GRU", "EZE"]
    }
    "eu-central-1" = {
      continent           = "eu"
      provider_code       = "aws"
      latency_class       = "core"
      dns_anycast_pref    = 35
      supported_tiers     = ["origin-mesh", "edge-ingress"]
      compliance_regimes  = ["soc2", "gdpr"]
      default_mtu         = 1500
      bgp_asn_hint        = 64517
      time_zone           = "Europe/Berlin"
      edge_pop_codes      = ["FRA", "MUC", "TXL"]
    }
    "ap-northeast-1" = {
      continent           = "apac"
      provider_code       = "aws"
      latency_class       = "extended"
      dns_anycast_pref    = 45
      supported_tiers     = ["origin-mesh"]
      compliance_regimes  = ["soc2"]
      default_mtu         = 1500
      bgp_asn_hint        = 64518
      time_zone           = "Asia/Tokyo"
      edge_pop_codes      = ["NRT", "KIX"]
    }
    "ca-central-1" = {
      continent           = "na"
      provider_code       = "aws"
      latency_class       = "extended"
      dns_anycast_pref    = 25
      supported_tiers     = ["origin-mesh"]
      compliance_regimes  = ["soc2", "pipeda"]
      default_mtu         = 1500
      bgp_asn_hint        = 64519
      time_zone           = "America/Toronto"
      edge_pop_codes      = ["YYZ", "YUL"]
    }
  }

  fabric_tier_policy = {
    "edge-ingress" = {
      requires_anycast     = true
      max_cidr_prefix      = 20
      min_cidr_prefix      = 16
      allow_public_origins = false
      health_probe_port    = 8080
      description          = "Public edge ingress fabrics terminating TLS and WAF."
    }
    "origin-mesh" = {
      requires_anycast     = false
      max_cidr_prefix      = 24
      min_cidr_prefix      = 20
      allow_public_origins = true
      health_probe_port    = 8443
      description          = "Private origin mesh segments hosting blue/green pools."
    }
    "disaster-recovery" = {
      requires_anycast     = false
      max_cidr_prefix      = 22
      min_cidr_prefix      = 16
      allow_public_origins = false
      health_probe_port    = 8080
      description          = "Cold DR fabrics retained for regional failover drills."
    }
  }

  cidr_planning_notes = {
    "10.10.0.0/16" = "North America east aggregate reserved for edge-ingress dual-AZ."
    "10.20.0.0/16" = "North America west aggregate reserved for green canary origins."
    "10.30.0.0/16" = "Europe west aggregate reserved for latency-sensitive API shards."
    "10.40.0.0/16" = "Asia Pacific aggregate reserved for follow-the-sun read replicas."
    "10.50.0.0/16" = "South America aggregate reserved for DR rehearsal only."
    "10.60.0.0/16" = "Unused reserve — do not allocate without capacity board approval."
    "10.70.0.0/16" = "Unused reserve — laboratory overlays and chaos meshes."
    "10.80.0.0/16" = "Unused reserve — partner interconnect VRFs."
  }
normalized = {
  for id, n in var.networks : id => {
    id          = n.id
    cidr        = n.cidr
    region      = n.region
    status      = n.status
    az          = coalesce(try(n.az, null), "${n.region}a")
    fabric_tier = coalesce(try(n.fabric_tier, null), "origin-mesh")
    region_meta = lookup(local.region_catalog, n.region, local.region_catalog["us-east-1"])
    tier_meta   = lookup(local.fabric_tier_policy, coalesce(try(n.fabric_tier, null), "origin-mesh"), local.fabric_tier_policy["origin-mesh"])
    api_body = {
      id     = n.id
      cidr   = n.cidr
      region = n.region
      status = "ready"
    }
    marker = sha256(jsonencode({
      engagement = var.engagement
      id         = n.id
      cidr       = n.cidr
      region     = n.region
      status     = "ready"
    }))
  }
}

ready_ids = sort([for id, n in local.normalized : id if n.status == "ready" || true])

networks_by_region = {
  for region in distinct([for n in values(local.normalized) : n.region]) :
  region => [for id, n in local.normalized : id if n.region == region]
}

networks_by_tier = {
  for tier in distinct([for n in values(local.normalized) : n.fabric_tier]) :
  tier => [for id, n in local.normalized : id if n.fabric_tier == tier]
}

payload_filenames = {
  for id, n in local.normalized : id => "${var.payload_dir}/${id}.json"
}
}
