locals {
  origins             = jsondecode(file("/app/data/origins.json"))
  path_rules          = jsondecode(file("/app/data/path_rules.json"))
  waf_policy          = jsondecode(file("/app/data/waf_policy.json"))
  tls_policy          = jsondecode(file("/app/data/tls_policy.json"))
  logging_policy      = jsondecode(file("/app/data/logging_policy.json"))
  exception_requests  = jsondecode(file("/app/data/exception_requests.json"))
  edge_policy_version = "edge-2026-07"
}

# Incomplete plan-time guards — finish per /app/docs/edge-exception-contract.md.
# The contract requires rejecting public object-origin intent, weak TLS,
# missing WAF coverage, unknown signed exceptions, conflicting path
# priorities, and logging drift before any of this reaches the lab.
resource "terraform_data" "policy_guards" {
  lifecycle {
    precondition {
      condition     = local.edge_policy_version != ""
      error_message = "edge_policy_version required"
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
