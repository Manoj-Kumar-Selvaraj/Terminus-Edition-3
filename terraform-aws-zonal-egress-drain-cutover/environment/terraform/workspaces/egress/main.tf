locals {
  topology = jsondecode(file("/app/data/topology.json"))
  services = jsondecode(file("/app/data/services.json"))
  defaults = jsondecode(file("/app/data/defaults.json"))
}

module "egress" {
  source = "../../modules/egress"

  name_prefix            = local.defaults.name_prefix
  region                 = local.defaults.region
  account_id             = local.defaults.account_id
  vpc_cidr               = local.topology.vpc_cidr
  azs                    = local.topology.azs
  nat_enabled_azs        = toset(local.defaults.nat_enabled_azs)
  allowed_principal_arns = local.defaults.allowed_principal_arns
  artifact_bucket_arns   = local.defaults.artifact_bucket_arns
  runtime_queue_name     = local.defaults.runtime_queue_name
  interface_services     = toset(local.services.interface)
  gateway_services       = toset(local.services.gateway)
  tags                   = local.defaults.tags
}

output "egress_route_matrix" {
  value = module.egress.egress_route_matrix
}

output "security_summary" {
  value = module.egress.security_summary
}
