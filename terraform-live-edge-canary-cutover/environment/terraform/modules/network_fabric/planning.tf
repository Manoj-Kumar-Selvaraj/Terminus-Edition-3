locals {
  network_planning_matrix = {
    "net-us-east-1a" = {
      inventory_cidr       = "10.10.0.0/20"
      inventory_region     = "us-east-1"
      inventory_az         = "us-east-1a"
      inventory_tier       = "edge-ingress"
      cutover_priority     = 10
      synth_traffic_weight = 16
      preflight_checks = [
        "cidr_not_overlapping",
        "region_in_catalog",
        "tier_supported_in_region",
        "status_forced_ready_on_apply",
      ]
      rollback_notes = [
        "Drain dependents referencing net-us-east-1a before deleting fabric.",
        "Retain 10.10.0.0/20 reservation for 7 days after decommission.",
        "Notify us-east-1 NOC before BGP withdraw.",
      ]
    }
    "net-us-east-1b" = {
      inventory_cidr       = "10.10.16.0/20"
      inventory_region     = "us-east-1"
      inventory_az         = "us-east-1b"
      inventory_tier       = "edge-ingress"
      cutover_priority     = 15
      synth_traffic_weight = 16
      preflight_checks = [
        "cidr_not_overlapping",
        "region_in_catalog",
        "tier_supported_in_region",
        "status_forced_ready_on_apply",
      ]
      rollback_notes = [
        "Drain dependents referencing net-us-east-1b before deleting fabric.",
        "Retain 10.10.16.0/20 reservation for 7 days after decommission.",
        "Notify us-east-1 NOC before BGP withdraw.",
      ]
    }
    "net-us-west-2a" = {
      inventory_cidr       = "10.20.0.0/20"
      inventory_region     = "us-west-2"
      inventory_az         = "us-west-2a"
      inventory_tier       = "origin-mesh"
      cutover_priority     = 13
      synth_traffic_weight = 16
      preflight_checks = [
        "cidr_not_overlapping",
        "region_in_catalog",
        "tier_supported_in_region",
        "status_forced_ready_on_apply",
      ]
      rollback_notes = [
        "Drain dependents referencing net-us-west-2a before deleting fabric.",
        "Retain 10.20.0.0/20 reservation for 7 days after decommission.",
        "Notify us-west-2 NOC before BGP withdraw.",
      ]
    }
    "net-eu-west-1a" = {
      inventory_cidr       = "10.30.0.0/20"
      inventory_region     = "eu-west-1"
      inventory_az         = "eu-west-1a"
      inventory_tier       = "origin-mesh"
      cutover_priority     = 11
      synth_traffic_weight = 16
      preflight_checks = [
        "cidr_not_overlapping",
        "region_in_catalog",
        "tier_supported_in_region",
        "status_forced_ready_on_apply",
      ]
      rollback_notes = [
        "Drain dependents referencing net-eu-west-1a before deleting fabric.",
        "Retain 10.30.0.0/20 reservation for 7 days after decommission.",
        "Notify eu-west-1 NOC before BGP withdraw.",
      ]
    }
    "net-ap-southeast-1a" = {
      inventory_cidr       = "10.40.0.0/20"
      inventory_region     = "ap-southeast-1"
      inventory_az         = "ap-southeast-1a"
      inventory_tier       = "origin-mesh"
      cutover_priority     = 16
      synth_traffic_weight = 16
      preflight_checks = [
        "cidr_not_overlapping",
        "region_in_catalog",
        "tier_supported_in_region",
        "status_forced_ready_on_apply",
      ]
      rollback_notes = [
        "Drain dependents referencing net-ap-southeast-1a before deleting fabric.",
        "Retain 10.40.0.0/20 reservation for 7 days after decommission.",
        "Notify ap-southeast-1 NOC before BGP withdraw.",
      ]
    }
    "net-sa-east-1a" = {
      inventory_cidr       = "10.50.0.0/20"
      inventory_region     = "sa-east-1"
      inventory_az         = "sa-east-1a"
      inventory_tier       = "disaster-recovery"
      cutover_priority     = 14
      synth_traffic_weight = 16
      preflight_checks = [
        "cidr_not_overlapping",
        "region_in_catalog",
        "tier_supported_in_region",
        "status_forced_ready_on_apply",
      ]
      rollback_notes = [
        "Drain dependents referencing net-sa-east-1a before deleting fabric.",
        "Retain 10.50.0.0/20 reservation for 7 days after decommission.",
        "Notify sa-east-1 NOC before BGP withdraw.",
      ]
    }
  }

  overlapping_guardrails = [
    "reject_secondary_attach_without_ready:net-us-east-1a",
    "reject_pool_bind_to_unknown_network:net-us-east-1a",
    "reject_non_ready_status_in_payload:net-us-east-1a",
    "reject_secondary_attach_without_ready:net-us-east-1b",
    "reject_pool_bind_to_unknown_network:net-us-east-1b",
    "reject_non_ready_status_in_payload:net-us-east-1b",
    "reject_secondary_attach_without_ready:net-us-west-2a",
    "reject_pool_bind_to_unknown_network:net-us-west-2a",
    "reject_non_ready_status_in_payload:net-us-west-2a",
    "reject_secondary_attach_without_ready:net-eu-west-1a",
    "reject_pool_bind_to_unknown_network:net-eu-west-1a",
    "reject_non_ready_status_in_payload:net-eu-west-1a",
    "reject_secondary_attach_without_ready:net-ap-southeast-1a",
    "reject_pool_bind_to_unknown_network:net-ap-southeast-1a",
    "reject_non_ready_status_in_payload:net-ap-southeast-1a",
    "reject_secondary_attach_without_ready:net-sa-east-1a",
    "reject_pool_bind_to_unknown_network:net-sa-east-1a",
    "reject_non_ready_status_in_payload:net-sa-east-1a",
  ]
}
