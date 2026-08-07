locals {
  origins             = jsondecode(file("/app/data/origins.json"))
  path_rules          = jsondecode(file("/app/data/path_rules.json"))
  waf_policy          = jsondecode(file("/app/data/waf_policy.json"))
  tls_policy          = jsondecode(file("/app/data/tls_policy.json"))
  logging_policy      = jsondecode(file("/app/data/logging_policy.json"))
  exception_requests  = jsondecode(file("/app/data/exception_requests.json"))
  edge_policy_version = "edge-2026-07"

  required_distributions = ["static-api", "failover", "signed-content"]

  public_origins = [
    for o in local.origins : o.origin_id
    if o.type == "s3" && try(o.public_access_allowed, false)
  ]

  priority_keys = [for r in local.path_rules : "${r.distribution}:${r.priority}"]
  duplicate_priorities = distinct([
    for k in local.priority_keys : k
    if length([for x in local.priority_keys : x if x == k]) > 1
  ])

  signed_rule_keys = toset([
    for r in local.path_rules : "${r.distribution}|${r.path}" if r.signed
  ])
  approved_exceptions = [for e in local.exception_requests : e if e.status == "approved"]
  unknown_exceptions = [
    for e in local.approved_exceptions : e.exception_id
    if !contains(local.signed_rule_keys, "${e.distribution}|${e.path_pattern}")
  ]

  logging_dists   = toset([for l in local.logging_policy : l.distribution])
  logging_buckets = distinct([for l in local.logging_policy : l.bucket])
}

# Plan-time guards per /app/docs/edge-exception-contract.md. Unsafe policy
# inputs must fail here, before the lab mutates any runtime state.
resource "terraform_data" "policy_guards" {
  lifecycle {
    precondition {
      condition     = local.edge_policy_version != ""
      error_message = "edge_policy_version required"
    }
    precondition {
      condition     = length(local.public_origins) == 0
      error_message = "public_access_allowed origins present: ${join(",", local.public_origins)}"
    }
    precondition {
      condition     = can(regex("^TLSv1\\.2", local.tls_policy.minimum_protocol))
      error_message = "TLS minimum_protocol below required floor: ${local.tls_policy.minimum_protocol}"
    }
    precondition {
      condition     = toset(local.waf_policy.distributions) == toset(local.required_distributions)
      error_message = "WAF coverage missing required edge(s)"
    }
    precondition {
      condition     = length(local.duplicate_priorities) == 0
      error_message = "conflicting path_rules priority: ${join(",", local.duplicate_priorities)}"
    }
    precondition {
      condition     = length(local.unknown_exceptions) == 0
      error_message = "unknown signed exception(s): ${join(",", local.unknown_exceptions)}"
    }
    precondition {
      condition     = local.logging_dists == toset(local.required_distributions)
      error_message = "logging_policy coverage drift"
    }
    precondition {
      condition     = length(local.logging_buckets) == 1
      error_message = "logging bucket drift across distributions"
    }
  }
}

module "edge" {
  source = "../../modules/edge"

  providers = {
    aws          = aws
    aws.failover = aws.failover
  }

  edge_policy_version = local.edge_policy_version
  origins             = local.origins
  path_rules          = local.path_rules
  waf_policy          = local.waf_policy
  tls_policy          = local.tls_policy
  logging_policy      = local.logging_policy
  exception_requests  = local.exception_requests

  depends_on = [terraform_data.policy_guards]
}

output "distribution_ids" {
  value = module.edge.distribution_ids
}

output "origin_access_control_ids" {
  value = module.edge.origin_access_control_ids
}

output "web_acl_arns" {
  value = module.edge.web_acl_arns
}

output "bucket_names" {
  value = module.edge.bucket_names
}

output "signed_path_patterns" {
  value = module.edge.signed_path_patterns
}
